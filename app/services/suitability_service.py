"""Airfoil suitability search service (gh-821, gh-825).

Implements GET /airfoils/db/suitability — resolves Re from chord/speed,
optionally resolves aeroplane context (UUID → mission + operating CLs),
queries the precomputed low-Re polar DB, scores three lenses, and returns
ranked results with a caveat block.

Three lenses (ranked desc by active_lens):
  1. re_agnostic — normalised quality from scalar metrics at query Re.
  2. mission     — re_agnostic × mission-weighting table (family/thickness/cl_max).
  3. target_cl_cruise — Match×Efficiency at the cruise CL; null when CL unavailable.

active_lens priority: mission (if resolved) > target_cl_cruise (if resolved) > re_agnostic.
active_lens is NEVER a glide point (target_cl_best_glide / target_cl_min_sink).

## Additive `include` parameter (gh-825 item 5)
search_suitability accepts an optional ``include: Optional[list[str]]`` kwarg.
Any airfoil name in ``include`` that genuinely has low-Re polar rows is ALWAYS
scored and returned, even if it falls outside the top-``limit`` ranked block.
Airfoils with NO polar rows are NOT fabricated — they are simply absent.
Names already in the top-N are NOT duplicated.
Ordering: top-N ranked block first (confidence-aware sort), then any included
extras that were dropped by the limit (appended in order of `include`).
Old clients omitting `include` get identical behaviour to before (include=None).

## Documented assumptions (gh-825)
- Re stays LOCAL (per xsec chord).
- Section CL ≈ whole-wing CL under the elliptical, untwisted ideal (top-down design target).
- Tip-Re CL_max collapse is NOT modelled — surfaced via tip_re_flag + cl_max_margin +
  caveat.ignores_tip_re_clmax_collapse.

## Target CL provenance
target_cl_provenance documents the reliability of the three resolved target CLs:
  - 'calculated' : mass row CALCULATED/auto AND v_cruise_auto=True in ctx
  - 'estimated'  : mass row ESTIMATE/manual OR v_cruise_auto absent/False
  - 'mixed'      : mass calculated but speed estimated (or vice versa)
  - Default 'estimated' when no aeroplane or no mass row.
"""

from __future__ import annotations

import logging
import math
import uuid as _uuid_module
from typing import Optional

from sqlalchemy.orm import Session

from app.models.aeroplanemodel import AeroplaneModel, DesignAssumptionModel
from app.models.airfoil import AirfoilModel
from app.models.airfoil_low_re import AirfoilGeometryModel, AirfoilLowRePolarModel
from app.models.mission_objective import MissionObjectiveModel
from app.schemas.airfoil import (
    SuitabilityCaveat,
    SuitabilityItem,
    SuitabilityQuery,
    SuitabilityResponse,
    TargetClProvenance,
)
from app.services.airfoil_low_re_service import (
    _level_flight_cl,
    compute_re_cd0_reference,
    interpolate_polar_at_re,
    score_mission,
    score_re_agnostic,
    score_target_cl,
)
from app.settings import Settings, get_settings

logger = logging.getLogger(__name__)

# ISA sea-level for Re computation (ν = μ/ρ ≈ 1.81e-5/1.225 m²/s)
_RHO = 1.225  # kg/m³
_MU = 1.81e-5  # Pa·s  dynamic viscosity

# MISSION enum → our internal weighting keys (5-key set: trainer|sport|aerobatic|glider|flying_wing)
#
# Maps every valid stored mission_type (MissionPreset.id values from
# mission_preset_seed.py) onto one of the five scoring-weight categories
# defined in Settings.low_re_mission_weights.
#
# Rule of thumb:
#   - Glider-type missions (pure soaring, self-launching) → "glider"
#   - Speed/racing missions → "sport"
#   - High-maneuver/3D/aerobatic missions → "aerobatic"
#   - STOL / high-CL / forgiving missions → "trainer"
#   - Tailless flying wings → "flying_wing"
_MISSION_TYPE_MAP = {
    # --- 1:1 passthrough for the 5 canonical weight keys ---
    "trainer": "trainer",
    "sport": "sport",
    "aerobatic": "aerobatic",
    "glider": "glider",
    "flying_wing": "flying_wing",
    # --- Seeded preset aliases (mission_preset_seed.py) ---
    # Sailplane / motor-glider family → glider weighting
    "sailplane": "glider",
    "motor_glider": "glider",
    "motorglider": "glider",  # legacy spelling without underscore
    "slope_soarer": "slope_soarer",  # gh-825 item 12: own weighting (thinner t/c, semi_sym/cambered)
    "thermal": "glider",  # forward-compat if "thermal" ever becomes a preset id
    "soarer": "glider",  # forward-compat
    # Wing-racer / FPV → sport (speed + moderate maneuver)
    "wing_racer": "sport",
    "fpv_cruiser": "sport",
    # Acrobatic 3D / warbird → aerobatic
    "acro_3d": "aerobatic",
    "warbird": "aerobatic",
    "three_d": "aerobatic",
    "3d": "aerobatic",
    # STOL / bush → trainer (high CL_max, forgiving stall)
    "stol_bush": "trainer",
    "stol": "trainer",
    "bush": "trainer",
}


def _compute_re(chord_m: float, speed_ms: float) -> float:
    """Compute Reynolds number: Re = ρ·V·c / μ."""
    return _RHO * speed_ms * chord_m / _MU


def _clamp_re_to_grid(re: float, grid: list[int]) -> tuple[float, bool]:
    """Clamp Re to nearest grid endpoint if out of range.

    Returns (clamped_re, re_clamped_flag).
    """
    if re <= grid[0]:
        return float(grid[0]), True
    if re >= grid[-1]:
        return float(grid[-1]), True
    return re, False


def _resolve_provenance(
    aeroplane: Optional[AeroplaneModel],
    db: Session,
    ctx: dict,
) -> TargetClProvenance:
    """Derive target_cl_provenance from the mass DesignAssumptionModel + v_cruise_auto.

    Rules:
      - No aeroplane / no mass row → 'estimated'
      - mass.active_source in ('CALCULATED', 'COMPUTED') AND ctx['v_cruise_auto'] is truthy
        → 'calculated'
      - mass.active_source in ('ESTIMATE', 'MANUAL') AND NOT v_cruise_auto
        → 'estimated'
      - Otherwise (one calculated, one estimated) → 'mixed'
    """
    if aeroplane is None:
        return "estimated"

    mass_row = (
        db.query(DesignAssumptionModel)
        .filter(
            DesignAssumptionModel.aeroplane_id == aeroplane.id,
            DesignAssumptionModel.parameter_name == "mass",
        )
        .first()
    )

    mass_is_calculated = False
    if mass_row is not None:
        src = (mass_row.active_source or "").upper()
        mass_is_calculated = src in ("CALCULATED", "COMPUTED", "AUTO")

    v_cruise_auto = bool(ctx.get("v_cruise_auto", False))

    if mass_is_calculated and v_cruise_auto:
        return "calculated"
    if not mass_is_calculated and not v_cruise_auto:
        return "estimated"
    # Mixed: one is calculated, the other is not
    return "mixed"


def search_suitability(
    db: Session,
    chord_m: float,
    speed_ms: float,
    *,
    aeroplane_id: Optional[str] = None,
    mission_type: Optional[str] = None,
    target_cl_cruise: Optional[float] = None,
    target_cl_best_glide: Optional[float] = None,
    target_cl_min_sink: Optional[float] = None,
    tip_chord_m: Optional[float] = None,
    limit: int = 50,
    include: Optional[list[str]] = None,
    settings: Optional[Settings] = None,
) -> SuitabilityResponse:
    """Search and rank airfoils by suitability at the given chord/speed.

    Parameters
    ----------
    db : Session           SQLAlchemy session.
    chord_m : float        Root chord in metres (for Re computation).
    speed_ms : float       Airspeed in m/s.
    aeroplane_id : str     Optional UUID4 string of an AeroplaneModel.
                           Resolves UUID→integer id via AeroplaneModel.uuid.
                           Unknown UUID → degrade to re_agnostic-only (no 500).
    mission_type : str     Optional explicit mission type (overrides model-derived).
    target_cl_cruise : float  Optional explicit override for cruise target CL.
    target_cl_best_glide : float  Optional explicit override for best-glide CL.
    target_cl_min_sink : float    Optional explicit override for min-sink CL
                           (renamed from target_cl_loiter).
    tip_chord_m : float    Optional tip chord for tip Re flag only.
    limit : int            Maximum results to return.
    include : list[str]    Optional list of airfoil names to ALWAYS score and return,
                           even if they fall outside the top-``limit`` ranked block.
                           - Only names with genuine low-Re polar rows are returned;
                             names with no data are NOT fabricated.
                           - Names already in the top-N are NOT duplicated.
                           - Included extras are appended AFTER the top-N block.
                           - None (default) → identical behaviour to before (no-op).
    settings : Settings    Application settings.  When omitted the module-level
                           lru-cached ``get_settings()`` is used — avoids
                           constructing a fresh ``Settings()`` per request.
                           Pass an explicit instance from the CLI or tests.

    ## Three target CLs
    target_cl_cruise    ← v_cruise_mps   (drives active_lens; can auto-rank)
    target_cl_best_glide ← v_md_mps     (display-only; never auto-ranks)
    target_cl_min_sink  ← v_min_sink_mps (display-only; never auto-ranks)

    Explicit params always override context-derived values.
    """
    if settings is None:
        settings = get_settings()
    re_grid = settings.low_re_grid
    mission_weights = settings.low_re_mission_weights
    low_conf_flag = settings.low_re_low_confidence_flag

    # --- Reynolds number at root chord ---
    re_root = _compute_re(chord_m, speed_ms)
    re_clamped_root, re_clamped = _clamp_re_to_grid(re_root, re_grid)

    # --- Tip Re flag ---
    # (gh-825 item 2) Flag is True if:
    #   - tip_Re < settings.low_re_tip_re_abs_floor  (absolute low-Re regime)
    #   OR
    #   - (re_root - re_tip) > settings.low_re_tip_re_rel_drop
    #     (tip Re is in a meaningfully different aerodynamic regime than root)
    # Both comparisons use the RAW (un-clamped) Re values from _compute_re.
    # Boundary: strictly less-than / strictly greater-than (edges are NOT flagged).
    tip_re_flag_all = False
    if tip_chord_m is not None:
        re_tip = _compute_re(tip_chord_m, speed_ms)
        tip_re_flag_all = (
            re_tip < settings.low_re_tip_re_abs_floor
            or (re_root - re_tip) > settings.low_re_tip_re_rel_drop
        )

    # --- Resolve aeroplane context ---
    effective_mission_type: Optional[str] = mission_type
    effective_target_cl_cruise: Optional[float] = target_cl_cruise
    effective_target_cl_best_glide: Optional[float] = target_cl_best_glide
    effective_target_cl_min_sink: Optional[float] = target_cl_min_sink

    aeroplane: Optional[AeroplaneModel] = None
    ctx: dict = {}
    provenance: TargetClProvenance = "estimated"

    if aeroplane_id is not None:
        # Guard: validate that aeroplane_id is a well-formed UUID before querying.
        # A malformed value (e.g. '9', 'not-a-uuid') would cause SQLAlchemy to
        # raise StatementError(ValueError('badly formed hexadecimal UUID string'))
        # leaking raw SQL into the response.  Treat any malformed id exactly like
        # an unknown-but-valid UUID — degrade to re_agnostic-only (gh-829).
        _is_valid_uuid = False
        try:
            _uuid_module.UUID(str(aeroplane_id))
            _is_valid_uuid = True
        except (ValueError, AttributeError):
            logger.warning(
                "Malformed aeroplane_id '%s' — degrading to re_agnostic-only (gh-829)",
                aeroplane_id,
            )

        if _is_valid_uuid:
            aeroplane = (
                db.query(AeroplaneModel).filter(AeroplaneModel.uuid == str(aeroplane_id)).first()
            )
            if aeroplane is None:
                logger.warning(
                    "Unknown aeroplane_id '%s' — degrading to re_agnostic-only", aeroplane_id
                )
            else:
                # Resolve mission type (explicit param overrides model value)
                if effective_mission_type is None:
                    mission_obj = (
                        db.query(MissionObjectiveModel)
                        .filter(MissionObjectiveModel.aeroplane_id == aeroplane.id)
                        .first()
                    )
                    if mission_obj is not None:
                        mapped = _MISSION_TYPE_MAP.get((mission_obj.mission_type or "").lower())
                        effective_mission_type = mapped  # may still be None if unmapped

                # Resolve operating CLs from assumption_computation_context
                ctx = getattr(aeroplane, "assumption_computation_context", None) or {}
                mass_kg: Optional[float] = ctx.get("mass_kg")
                v_cruise_mps: Optional[float] = ctx.get("v_cruise_mps")
                v_md_mps: Optional[float] = ctx.get("v_md_mps")  # best-glide speed (NEW)
                v_min_sink_mps: Optional[float] = ctx.get("v_min_sink_mps")
                s_ref_m2: Optional[float] = ctx.get("s_ref_m2")

                # Compute cruise CL (explicit param overrides derived)
                if effective_target_cl_cruise is None:
                    if all(v is not None for v in (mass_kg, v_cruise_mps, s_ref_m2)):
                        try:
                            effective_target_cl_cruise = _level_flight_cl(
                                mass_kg, v_cruise_mps, s_ref_m2
                            )
                        except (ValueError, ZeroDivisionError):
                            effective_target_cl_cruise = None

                # Compute best-glide CL from v_md_mps (explicit param overrides derived)
                if effective_target_cl_best_glide is None:
                    if all(v is not None for v in (mass_kg, v_md_mps, s_ref_m2)):
                        try:
                            effective_target_cl_best_glide = _level_flight_cl(
                                mass_kg, v_md_mps, s_ref_m2
                            )
                        except (ValueError, ZeroDivisionError):
                            effective_target_cl_best_glide = None

                # Compute min-sink CL (renamed from loiter; explicit param overrides derived)
                if effective_target_cl_min_sink is None:
                    if all(v is not None for v in (mass_kg, v_min_sink_mps, s_ref_m2)):
                        try:
                            effective_target_cl_min_sink = _level_flight_cl(
                                mass_kg, v_min_sink_mps, s_ref_m2
                            )
                        except (ValueError, ZeroDivisionError):
                            effective_target_cl_min_sink = None

    # --- Provenance ---
    provenance = _resolve_provenance(aeroplane, db, ctx)

    # --- Query DB: all airfoil geometries + polars ---
    geo_rows = db.query(AirfoilGeometryModel).all()
    # Index geometry by airfoil_name
    geo_by_name = {g.airfoil_name: g for g in geo_rows}

    # Load all polar rows for all airfoils (batch query)
    polar_rows = db.query(AirfoilLowRePolarModel).all()
    polars_by_name: dict[str, list] = {}
    for p in polar_rows:
        polars_by_name.setdefault(p.airfoil_name, []).append(p)

    # --- Per-Re cd0 reference (computed once for the request) ---
    re_cd0_ref = compute_re_cd0_reference(polars_by_name, re_clamped_root)

    # --- Score each airfoil ---
    items: list[SuitabilityItem] = []
    recommend_xfoil = False

    for name, geo in geo_by_name.items():
        rows = polars_by_name.get(name, [])
        polar = interpolate_polar_at_re(rows, re_clamped_root, re_grid)

        re_agn = score_re_agnostic(polar)
        if re_agn is None:
            re_agn = 0.0

        # Mission lens
        mission_score: Optional[float] = None
        if effective_mission_type is not None:
            mission_score = score_mission(
                re_agnostic=re_agn,
                family=geo.family,
                max_thickness_pct=geo.max_thickness_pct,
                cl_max=polar.get("cl_max") if polar else None,
                mission_type=effective_mission_type,
                mission_weights=mission_weights,
            )

        # Target CL lenses — cruise can auto-rank; glide points are display-only
        cl_cruise_score: Optional[float] = None
        if effective_target_cl_cruise is not None and polar is not None:
            cl_cruise_score = score_target_cl(
                polar,
                effective_target_cl_cruise,
                re_cd0_reference=re_cd0_ref,
                settings=settings,
            )

        cl_best_glide_score: Optional[float] = None
        if effective_target_cl_best_glide is not None and polar is not None:
            cl_best_glide_score = score_target_cl(
                polar,
                effective_target_cl_best_glide,
                re_cd0_reference=re_cd0_ref,
                settings=settings,
            )

        cl_min_sink_score: Optional[float] = None
        if effective_target_cl_min_sink is not None and polar is not None:
            cl_min_sink_score = score_target_cl(
                polar,
                effective_target_cl_min_sink,
                re_cd0_reference=re_cd0_ref,
                settings=settings,
            )

        # stall_gentleness — raw from polar
        stall_gentleness: Optional[float] = polar.get("stall_gentleness") if polar else None

        # cl_max_margin = cl_max − max(resolved target CLs present)
        cl_max_margin: Optional[float] = None
        if polar is not None:
            cl_max_val = polar.get("cl_max")
            if cl_max_val is not None:
                # Collect all resolved target CLs
                target_cls = [
                    v
                    for v in (
                        effective_target_cl_cruise,
                        effective_target_cl_best_glide,
                        effective_target_cl_min_sink,
                    )
                    if v is not None
                ]
                if target_cls:
                    cl_max_margin = cl_max_val - max(target_cls)

        # min_analysis_confidence
        min_conf = polar.get("min_analysis_confidence") if polar else None
        if min_conf is None:
            min_conf = 0.0
        if min_conf < low_conf_flag:
            recommend_xfoil = True

        # Per-item caveat
        item_caveat = ""
        if min_conf < low_conf_flag:
            item_caveat = "Low analysis confidence — validate with XFoil."

        items.append(
            SuitabilityItem(
                airfoil_name=name,
                family=geo.family,
                re_agnostic=re_agn,
                mission=mission_score,
                target_cl_cruise=cl_cruise_score,
                target_cl_best_glide=cl_best_glide_score,
                target_cl_min_sink=cl_min_sink_score,
                stall_gentleness=stall_gentleness,
                cl_max_margin=cl_max_margin,
                min_analysis_confidence=min_conf,
                tip_re_flag=tip_re_flag_all,
                caveat=item_caveat,
            )
        )

    # --- Determine active lens and rank ---
    # Confidence-aware sort key (BUG-3 fix, gh-821):
    #   Primary:   confident items first (min_analysis_confidence >= low_conf_flag)
    #   Secondary: active-lens score descending within each confidence tier
    # The *displayed* scores (re_agnostic / mission / target_cl_cruise) are
    # intentionally unchanged — only the sort position is confidence-aware.
    #
    # RANKING RULE (gh-825):
    #   active_lens chosen by priority:
    #     1. 'mission'           — if any item.mission is not None
    #     2. 'target_cl_cruise'  — else if any item.target_cl_cruise is not None
    #     3. 're_agnostic'       — otherwise
    #   Glide points NEVER auto-rank (never assigned to active_lens).
    has_mission = any(item.mission is not None for item in items)
    has_cruise = any(item.target_cl_cruise is not None for item in items)

    def _conf_tier(item: SuitabilityItem) -> int:
        """Return 0 for confident items (ranked first), 1 for low-confidence."""
        return 0 if item.min_analysis_confidence >= low_conf_flag else 1

    if has_mission:
        active_lens = "mission"
        items.sort(key=lambda i: (_conf_tier(i), -(i.mission or 0.0)))
    elif has_cruise:
        active_lens = "target_cl_cruise"
        items.sort(key=lambda i: (_conf_tier(i), -(i.target_cl_cruise or 0.0)))
    else:
        active_lens = "re_agnostic"
        items.sort(key=lambda i: (_conf_tier(i), -i.re_agnostic))

    # Save full scored+sorted list before applying limit (needed for include extras)
    all_items = list(items)

    # Apply limit
    items = items[:limit]

    # --- Additive `include` extras (gh-825 item 5) ---
    # Append items whose airfoil_name is in `include` but were dropped by the limit.
    # Only genuine entries (with scored polar rows, re_agnostic > 0 or has been scored)
    # are appended; names with no geometry/polar data are not fabricated.
    # De-duplication: skip names already present in the top-N block.
    if include:
        # Build a lookup from the full (pre-limit) scored set, keyed by lowercase name
        all_items_by_name: dict[str, SuitabilityItem] = {
            item.airfoil_name.lower(): item for item in all_items
        }
        present_names = {item.airfoil_name.lower() for item in items}
        for name_raw in include:
            name_lower = name_raw.strip().lower()
            if not name_lower:
                continue
            if name_lower in present_names:
                continue  # already in top-N — no duplicate
            candidate = all_items_by_name.get(name_lower)
            if candidate is None:
                continue  # no geometry row at all — not fabricated
            # Only include if the airfoil genuinely has polar rows
            # (polars_by_name is populated only for airfoils with rows)
            # Match against geo_by_name keys (case-insensitive)
            has_polars = any(n.lower() == name_lower for n in polars_by_name)
            if not has_polars:
                continue  # no polar data — not fabricated
            items.append(candidate)
            present_names.add(name_lower)

    # --- Build response ---
    caveat_text = (
        "Relative ranking only. "
        "No hysteresis or laminar-bubble modelling. "
        "Section CL ≈ wing CL (ideal elliptic, untwisted). "
        "Tip-Re CL_max collapse not modelled — check tip_re_flag and cl_max_margin."
    )
    if recommend_xfoil:
        caveat_text += (
            " Some airfoils have low analysis confidence — "
            "validation with XFoil or wind tunnel recommended."
        )

    query = SuitabilityQuery(
        chord_m=chord_m,
        speed_ms=speed_ms,
        reynolds=re_clamped_root,
        re_clamped=re_clamped,
        mission_type=effective_mission_type,
        target_cl_cruise=effective_target_cl_cruise,
        target_cl_best_glide=effective_target_cl_best_glide,
        target_cl_min_sink=effective_target_cl_min_sink,
        target_cl_provenance=provenance,
        active_lens=active_lens,
    )
    caveat = SuitabilityCaveat(
        relative_ranking_only=True,
        no_hysteresis_modelling=True,
        ignores_tip_re_clmax_collapse=True,
        recommend_xfoil_validation=recommend_xfoil,
        text=caveat_text,
    )

    return SuitabilityResponse(query=query, caveat=caveat, results=items)
