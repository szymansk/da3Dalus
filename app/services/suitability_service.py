"""Airfoil suitability search service (gh-821).

Implements GET /airfoils/db/suitability — resolves Re from chord/speed,
optionally resolves aeroplane context (UUID → mission + operating CLs),
queries the precomputed low-Re polar DB, scores three lenses, and returns
ranked results with a caveat block.

Three lenses (ranked desc by active_lens):
  1. re_agnostic — normalised quality from scalar metrics at query Re.
  2. mission     — re_agnostic × mission-weighting table (family/thickness/cl_max).
  3. target_cl_cruise — CD(CL_target) from parabolic fit; null when CL unavailable.

active_lens priority: mission (if resolved) > target_cl_cruise (if resolved) > re_agnostic.
active_lens is NEVER 'target_cl_loiter' (loiter is display-only).
"""

from __future__ import annotations

import logging
import math
from typing import Optional

from sqlalchemy.orm import Session

from app.models.aeroplanemodel import AeroplaneModel
from app.models.airfoil import AirfoilModel
from app.models.airfoil_low_re import AirfoilGeometryModel, AirfoilLowRePolarModel
from app.models.mission_objective import MissionObjectiveModel
from app.schemas.airfoil import (
    SuitabilityCaveat,
    SuitabilityItem,
    SuitabilityQuery,
    SuitabilityResponse,
)
from app.services.airfoil_low_re_service import (
    _level_flight_cl,
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
    "slope_soarer": "glider",  # slope soarer is aerobatic-capable but glider in airfoil needs
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


def search_suitability(
    db: Session,
    chord_m: float,
    speed_ms: float,
    *,
    aeroplane_id: Optional[str] = None,
    mission_type: Optional[str] = None,
    target_cl_cruise: Optional[float] = None,
    target_cl_loiter: Optional[float] = None,
    tip_chord_m: Optional[float] = None,
    limit: int = 50,
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
    target_cl_loiter : float  Optional explicit override for loiter target CL.
    tip_chord_m : float    Optional tip chord for tip Re flag only.
    limit : int            Maximum results to return.
    settings : Settings    Application settings.  When omitted the module-level
                           lru-cached ``get_settings()`` is used — avoids
                           constructing a fresh ``Settings()`` per request.
                           Pass an explicit instance from the CLI or tests.
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
    tip_re_flag_all = False
    if tip_chord_m is not None:
        re_tip = _compute_re(tip_chord_m, speed_ms)
        tip_re_flag_all = re_tip < re_root

    # --- Resolve aeroplane context ---
    effective_mission_type: Optional[str] = mission_type
    effective_target_cl_cruise: Optional[float] = target_cl_cruise
    effective_target_cl_loiter: Optional[float] = target_cl_loiter

    if aeroplane_id is not None:
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

            # Compute loiter CL (explicit param overrides derived)
            if effective_target_cl_loiter is None:
                if all(v is not None for v in (mass_kg, v_min_sink_mps, s_ref_m2)):
                    try:
                        effective_target_cl_loiter = _level_flight_cl(
                            mass_kg, v_min_sink_mps, s_ref_m2
                        )
                    except (ValueError, ZeroDivisionError):
                        effective_target_cl_loiter = None

    # --- Query DB: all airfoil geometries + polars ---
    geo_rows = db.query(AirfoilGeometryModel).all()
    # Index geometry by airfoil_name
    geo_by_name = {g.airfoil_name: g for g in geo_rows}

    # Load all polar rows for all airfoils (batch query)
    polar_rows = db.query(AirfoilLowRePolarModel).all()
    polars_by_name: dict[str, list] = {}
    for p in polar_rows:
        polars_by_name.setdefault(p.airfoil_name, []).append(p)

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

        # Target CL lenses
        cl_cruise_score: Optional[float] = None
        if effective_target_cl_cruise is not None and polar is not None:
            cl_cruise_score = score_target_cl(polar, effective_target_cl_cruise)

        cl_loiter_score: Optional[float] = None
        if effective_target_cl_loiter is not None and polar is not None:
            cl_loiter_score = score_target_cl(polar, effective_target_cl_loiter)

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
                target_cl_loiter=cl_loiter_score,
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

    # Apply limit
    items = items[:limit]

    # --- Build response ---
    caveat_text = "Relative ranking only. No hysteresis or laminar-bubble modelling. "
    if recommend_xfoil:
        caveat_text += (
            "Some airfoils have low analysis confidence — "
            "validation with XFoil or wind tunnel recommended."
        )

    query = SuitabilityQuery(
        chord_m=chord_m,
        speed_ms=speed_ms,
        reynolds=re_clamped_root,
        re_clamped=re_clamped,
        mission_type=effective_mission_type,
        target_cl_cruise=effective_target_cl_cruise,
        target_cl_loiter=effective_target_cl_loiter,
        active_lens=active_lens,
    )
    caveat = SuitabilityCaveat(
        relative_ranking_only=True,
        no_hysteresis_modelling=True,
        recommend_xfoil_validation=recommend_xfoil,
        text=caveat_text,
    )

    return SuitabilityResponse(query=query, caveat=caveat, results=items)
