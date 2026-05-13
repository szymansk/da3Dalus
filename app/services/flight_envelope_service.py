"""Flight envelope service — V-n curve computation, KPI derivation, and DB persistence.

Gust envelope (gh-487):
  Discrete sharp-edged vertical gust — Pratt-Walker model (NACA TN 2964).
  Gust alleviation factor K_g per FAR-25.341(a)(2) / CS-VLA.333.
  U_gust values from CS-VLA.333(c)(1) / FAR-23.333(c):
    V_C: 15.24 m/s (50 ft/s EAS)
    V_D:  7.62 m/s (25 ft/s EAS)
  CL_α from assumption_computation_context["cl_alpha_per_rad"] (alpha-sweep
  regression); falls back to Helmbold-Diederich (Anderson 6e Eq. 5.81) when
  context is unavailable.
  Mean Geometric Chord c̄ = S_ref / b_ref (not MAC) — see gh-487 spec.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import InternalError, NotFoundError
from app.models.aeroplanemodel import AeroplaneModel
from app.models.analysismodels import OperatingPointModel
from app.models.flight_envelope_model import FlightEnvelopeModel
from app.schemas.design_assumption import PARAMETER_DEFAULTS
from app.schemas.flight_envelope import (
    FlightEnvelopeRead,
    GustCriticalWarning,
    GustValidityWarning,
    PerformanceKPI,
    VnCurve,
    VnMarker,
    VnPoint,
)

logger = logging.getLogger(__name__)

GRAVITY = 9.81

# Gust speeds per CS-VLA.333(c)(1) / FAR-23.333(c) — sharp-edged EAS
GUST_U_VC_MPS: float = 15.24  # 50 ft/s at cruise speed V_C
GUST_U_VD_MPS: float = 7.62  # 25 ft/s at dive speed V_D

# Pratt-Walker μ_g validity range (NACA TN 2964 / FAR-25.341 applicability)
_MU_G_MIN: float = 3.0
_MU_G_MAX: float = 200.0


# ---------------------------------------------------------------------------
# Gust-envelope computation helpers (Pratt-Walker / FAR-25.341 / CS-VLA.333)
# ---------------------------------------------------------------------------


def _helmbold_cl_alpha(ar: float) -> float:
    """Finite-span CL_α by Helmbold-Diederich (Anderson 6e Eq. 5.81).

    CL_α = 2π·AR / (AR + 2)

    Used as cold-start fallback when no alpha-sweep is available.
    Explicitly NOT the thin-airfoil 2π limit — that overestimates CL_α
    at AR=6 by ~39%, producing unrealistically high gust loads.

    Sources: Anderson, Introduction to Flight, 6th ed., §5.3.
    """
    return 2.0 * math.pi * ar / (ar + 2.0)


def _compute_mu_g(
    mass_kg: float,
    s_ref: float,
    c_mgc: float,
    cl_alpha: float,
    rho: float = 1.225,
    g: float = GRAVITY,
) -> float:
    """Gust mass ratio μ_g (dimensionless).

    μ_g = 2·(W/S) / (ρ·c̄·CL_α·g)

    where c̄ = S_ref / b_ref  (Mean Geometric Chord, **not** MAC).
    For trapezoidal wings MGC ≈ MAC; for double-trapezoid the difference
    can be relevant (see gh-487 spec, issue body §AC section).

    Sources: FAR-25.341(a)(2); NACA TN 2964 (Pratt & Walker, 1953).
    """
    wing_loading = mass_kg * g / s_ref  # W/S in N/m²
    return 2.0 * wing_loading / (rho * c_mgc * cl_alpha * g)


def _compute_k_g(mu_g: float) -> float:
    """Gust alleviation factor K_g (dimensionless).

    K_g = 0.88·μ_g / (5.3 + μ_g)

    Emits a WARNING when μ_g is outside the Pratt validity range [3, 200]:
    - μ_g < 3  → very light/small aircraft; K_g may be optimistic.
    - μ_g > 200 → very large/heavy aircraft; formula may be conservative.

    Sources: FAR-25.341(a)(2); CS-VLA.333; NACA TN 2964.
    """
    if mu_g < _MU_G_MIN or mu_g > _MU_G_MAX:
        logger.warning(
            "μ_g = %.3f is outside Pratt validity range [%.0f, %.0f]. "
            "Gust alleviation factor K_g may be inaccurate "
            "(ref: NACA TN 2964 / FAR-25.341).",
            mu_g,
            _MU_G_MIN,
            _MU_G_MAX,
        )
    return 0.88 * mu_g / (5.3 + mu_g)


def _compute_delta_n(
    rho: float,
    v: float,
    cl_alpha: float,
    u_gust: float,
    k_g: float,
    mass_kg: float,
    s_ref: float,
    g: float = GRAVITY,
) -> float:
    """Gust load-factor increment Δn (dimensionless).

    Pratt-Walker discrete sharp-edged gust:

        ΔL = ½·ρ·V·S·CL_α·U_gust·K_g
        Δn = ΔL / W = ½·ρ·V·CL_α·U_gust·K_g / (W/S)

    Sources: FAR-25.341(a); CS-VLA.341; NACA TN 2964 (Pratt & Walker, 1953);
    Anderson, Introduction to Flight, 6th ed. §6.5.
    """
    wing_loading = mass_kg * g / s_ref  # W/S in N/m²
    return 0.5 * rho * v * cl_alpha * u_gust * k_g / wing_loading


def _extract_cl_alpha_from_context(ctx: dict) -> float | None:
    """Return cl_alpha_per_rad from the assumption computation context.

    Returns None when the key is absent or the value is not a finite number
    (guards against corrupted context caches).
    """
    val = ctx.get("cl_alpha_per_rad")
    if val is None:
        return None
    try:
        fval = float(val)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(fval) or fval <= 0:
        return None
    return fval


def _build_gust_lines(
    mass_kg: float,
    wing_area_m2: float,
    b_ref_m: float,
    cl_alpha: float,
    g_limit: float,
    v_stall: float,
    v_dive: float,
    rho: float = 1.225,
    gust_u_vc_mps: float = GUST_U_VC_MPS,
    gust_u_vd_mps: float = GUST_U_VD_MPS,
    n_points: int = 60,
) -> tuple[list[VnPoint], list[VnPoint], list[GustCriticalWarning | GustValidityWarning]]:
    """Compute positive and negative gust load-factor lines.

    Returns (gust_lines_positive, gust_lines_negative, warnings).

    The gust lines run from V_stall to V_dive.  U_gust is linearly
    interpolated between U_vc (at V_C = v_dive / 1.4) and U_vd (at V_dive).
    Below V_C, U_vc is used (conservative per CS-VLA.333(c)(1)).

    GustCriticalWarning is emitted at any point where 1+Δn > g_limit
    (positive) or 1-Δn < -0.4·g_limit (negative).

    GustValidityWarning is emitted when μ_g ∉ [3, 200] — the Pratt-Walker
    formula is only validated in this range (NACA TN 2964). RC/UAV with low
    W/S frequently produce μ_g < 3, making gust loads potentially optimistic
    (gh-497).
    """
    c_mgc = wing_area_m2 / b_ref_m  # Mean Geometric Chord = S/b (not MAC)
    mu_g = _compute_mu_g(mass_kg, wing_area_m2, c_mgc, cl_alpha, rho)
    k_g = _compute_k_g(mu_g)

    v_c = v_dive / 1.4  # Cruise speed (V_D = 1.4 · V_C by construction)

    positive: list[VnPoint] = []
    negative: list[VnPoint] = []
    warnings: list[GustCriticalWarning | GustValidityWarning] = []
    warned_positive = False
    warned_negative = False

    # Emit structured validity warning when μ_g is outside Pratt-Walker range
    if mu_g < _MU_G_MIN:
        warnings.append(
            GustValidityWarning(
                mu_g_value=round(mu_g, 4),
                validity_min=_MU_G_MIN,
                validity_max=_MU_G_MAX,
                message=(
                    f"μ_g={mu_g:.2f} is outside Pratt-Walker validity range "
                    f"[{_MU_G_MIN:.0f}, {_MU_G_MAX:.0f}]. "
                    "Gust loads may be optimistic for this light/small aircraft "
                    "(ref: NACA TN 2964 / FAR-25.341)."
                ),
            )
        )
    elif mu_g > _MU_G_MAX:
        warnings.append(
            GustValidityWarning(
                mu_g_value=round(mu_g, 4),
                validity_min=_MU_G_MIN,
                validity_max=_MU_G_MAX,
                message=(
                    f"μ_g={mu_g:.2f} is outside Pratt-Walker validity range "
                    f"[{_MU_G_MIN:.0f}, {_MU_G_MAX:.0f}]. "
                    "Gust loads may be conservative for this heavy aircraft "
                    "(ref: NACA TN 2964 / FAR-25.341)."
                ),
            )
        )

    for i in range(n_points):
        v = v_stall + (v_dive - v_stall) * i / (n_points - 1)

        # U_gust: constant at U_vc below V_C; linearly taper to U_vd at V_D
        if v <= v_c:
            u = gust_u_vc_mps
        else:
            # Linear interpolation from U_vc at V_C to U_vd at V_D
            frac = (v - v_c) / (v_dive - v_c)
            u = gust_u_vc_mps + frac * (gust_u_vd_mps - gust_u_vc_mps)

        delta_n = _compute_delta_n(rho, v, cl_alpha, u, k_g, mass_kg, wing_area_m2)
        n_pos = 1.0 + delta_n
        n_neg = 1.0 - delta_n

        positive.append(VnPoint(velocity_mps=round(v, 6), load_factor=round(n_pos, 6)))
        negative.append(VnPoint(velocity_mps=round(v, 6), load_factor=round(n_neg, 6)))

        if n_pos > g_limit and not warned_positive:
            warned_positive = True
            warnings.append(
                GustCriticalWarning(
                    velocity_mps=round(v, 4),
                    n_gust=round(n_pos, 4),
                    g_limit=round(g_limit, 4),
                    message=(
                        f"Gust-critical: gust load factor {n_pos:.2f}g exceeds "
                        f"maneuver limit {g_limit:.2f}g at V={v:.1f} m/s. "
                        "Structure must be sized by gust loads, not maneuver loads."
                    ),
                )
            )
        if n_neg < -0.4 * g_limit and not warned_negative:
            warned_negative = True
            warnings.append(
                GustCriticalWarning(
                    velocity_mps=round(v, 4),
                    n_gust=round(n_neg, 4),
                    g_limit=round(-0.4 * g_limit, 4),
                    message=(
                        f"Gust-critical: negative gust load factor {n_neg:.2f}g "
                        f"exceeds negative maneuver limit {-0.4 * g_limit:.2f}g "
                        f"at V={v:.1f} m/s."
                    ),
                )
            )

    return positive, negative, warnings


# ---------------------------------------------------------------------------
# Pure computation helpers (no DB)
# ---------------------------------------------------------------------------


def compute_vn_curve(
    mass_kg: float,
    cl_max: float,
    g_limit: float,
    wing_area_m2: float,
    rho: float = 1.225,
    v_max_mps: float = 28.0,
    b_ref_m: float | None = None,
    cl_alpha_per_rad: float | None = None,
    gust_u_vc_mps: float = GUST_U_VC_MPS,
    gust_u_vd_mps: float = GUST_U_VD_MPS,
) -> VnCurve:
    """Compute the V-n diagram boundary curves, including gust envelope.

    Returns a VnCurve with positive and negative maneuver boundary points
    from stall speed to dive speed (1.4 * v_max), plus optional gust lines.

    Gust lines require CL_α (from cl_alpha_per_rad or Helmbold fallback)
    AND b_ref_m (for MGC = S/b calculation of μ_g).  When neither is
    available, gust_lines_positive / negative remain empty.

    Gust model:
      Discrete sharp-edged gust per Pratt-Walker (NACA TN 2964).
      K_g per FAR-25.341(a)(2) / CS-VLA.333.
      Default U_gust: 15.24 m/s at V_C, 7.62 m/s at V_D
      (CS-VLA.333(c)(1) / FAR-23.333(c)).
    """
    if mass_kg <= 0 or cl_max <= 0 or wing_area_m2 <= 0 or v_max_mps <= 0:
        raise ValueError("mass_kg, cl_max, wing_area_m2, and v_max_mps must be positive")

    weight = mass_kg * GRAVITY
    v_stall = math.sqrt(2 * weight / (rho * wing_area_m2 * cl_max))
    v_dive = 1.4 * v_max_mps
    cl_min = -0.8 * cl_max

    n_points = 60  # > 50 as required

    positive: list[VnPoint] = []
    negative: list[VnPoint] = []

    for i in range(n_points):
        v = v_stall + (v_dive - v_stall) * i / (n_points - 1)
        q = 0.5 * rho * v**2

        n_pos = min(q * wing_area_m2 * cl_max / weight, g_limit)
        n_neg = max(q * wing_area_m2 * cl_min / weight, -0.4 * g_limit)

        positive.append(VnPoint(velocity_mps=round(v, 6), load_factor=round(n_pos, 6)))
        negative.append(VnPoint(velocity_mps=round(v, 6), load_factor=round(n_neg, 6)))

    # --- Gust envelope (Pratt-Walker) ----------------------------------------
    # Requires CL_α and wingspan (for MGC = S/b).
    # CL_α: prefer supplied value; fall back to Helmbold-Diederich if b_ref_m
    # is known (AR derivable from S and b); else skip gust lines.
    gust_lines_positive: list[VnPoint] = []
    gust_lines_negative: list[VnPoint] = []
    gust_warnings: list[GustCriticalWarning] = []

    effective_cl_alpha: float | None = cl_alpha_per_rad
    if effective_cl_alpha is None and b_ref_m is not None and b_ref_m > 0:
        ar = (b_ref_m**2) / wing_area_m2
        effective_cl_alpha = _helmbold_cl_alpha(ar)

    if effective_cl_alpha is not None and b_ref_m is not None and b_ref_m > 0:
        gust_lines_positive, gust_lines_negative, gust_warnings = _build_gust_lines(
            mass_kg=mass_kg,
            wing_area_m2=wing_area_m2,
            b_ref_m=b_ref_m,
            cl_alpha=effective_cl_alpha,
            g_limit=g_limit,
            v_stall=v_stall,
            v_dive=v_dive,
            rho=rho,
            gust_u_vc_mps=gust_u_vc_mps,
            gust_u_vd_mps=gust_u_vd_mps,
        )

    return VnCurve(
        positive=positive,
        negative=negative,
        dive_speed_mps=round(v_dive, 6),
        stall_speed_mps=round(v_stall, 6),
        gust_lines_positive=gust_lines_positive,
        gust_lines_negative=gust_lines_negative,
        gust_warnings=gust_warnings,
    )


def derive_performance_kpis(
    stall_speed_mps: float,
    v_max_mps: float,
    g_limit: float,
    markers: list[VnMarker],
    v_md_polar_mps: float | None = None,
    v_min_sink_polar_mps: float | None = None,
) -> list[PerformanceKPI]:
    """Derive 6 KPIs from the flight envelope and operating-point markers.

    Always returns exactly 6 KPIs: stall_speed, best_ld_speed,
    min_sink_speed, max_speed, max_load_factor, dive_speed.

    Precedence for ``best_ld_speed`` and ``min_sink_speed``:
    1. TRIMMED operating-point marker — confidence ``"trimmed"``
    2. Polar-derived value (``v_md_polar_mps`` / ``v_min_sink_polar_mps``)
       from ``assumption_computation_context`` — confidence ``"computed"``
    3. Heuristic multiplier of ``V_s`` (1.4·V_s and 1.2·V_s) —
       confidence ``"estimated"`` (gh-475 audit §4.1; this is wrong by
       up to 15 % for high-AR airframes and is kept only for the cold-start
       case where no polar has been computed yet).
    """
    markers_by_label: dict[str, VnMarker] = {m.label: m for m in markers}

    kpis: list[PerformanceKPI] = []

    # 1. stall_speed
    kpis.append(
        PerformanceKPI(
            label="stall_speed",
            display_name="Stall Speed",
            value=round(stall_speed_mps, 4),
            unit="m/s",
            source_op_id=None,
            confidence="limit",
        )
    )

    # 2. best_ld_speed
    best_ld_marker = markers_by_label.get("best_ld")
    if best_ld_marker is not None:
        kpis.append(
            PerformanceKPI(
                label="best_ld_speed",
                display_name="Best L/D Speed",
                value=round(best_ld_marker.velocity_mps, 4),
                unit="m/s",
                source_op_id=best_ld_marker.op_id,
                confidence="trimmed",
            )
        )
    elif v_md_polar_mps is not None and v_md_polar_mps > 0:
        kpis.append(
            PerformanceKPI(
                label="best_ld_speed",
                display_name="Best L/D Speed",
                value=round(v_md_polar_mps, 4),
                unit="m/s",
                source_op_id=None,
                confidence="computed",
            )
        )
    else:
        kpis.append(
            PerformanceKPI(
                label="best_ld_speed",
                display_name="Best L/D Speed",
                value=round(1.4 * stall_speed_mps, 4),
                unit="m/s",
                source_op_id=None,
                confidence="estimated",
            )
        )

    # 3. min_sink_speed
    min_sink_marker = markers_by_label.get("min_sink")
    if min_sink_marker is not None:
        kpis.append(
            PerformanceKPI(
                label="min_sink_speed",
                display_name="Min Sink Speed",
                value=round(min_sink_marker.velocity_mps, 4),
                unit="m/s",
                source_op_id=min_sink_marker.op_id,
                confidence="trimmed",
            )
        )
    elif v_min_sink_polar_mps is not None and v_min_sink_polar_mps > 0:
        kpis.append(
            PerformanceKPI(
                label="min_sink_speed",
                display_name="Min Sink Speed",
                value=round(v_min_sink_polar_mps, 4),
                unit="m/s",
                source_op_id=None,
                confidence="computed",
            )
        )
    else:
        kpis.append(
            PerformanceKPI(
                label="min_sink_speed",
                display_name="Min Sink Speed",
                value=round(1.2 * stall_speed_mps, 4),
                unit="m/s",
                source_op_id=None,
                confidence="estimated",
            )
        )

    # 4. max_speed
    kpis.append(
        PerformanceKPI(
            label="max_speed",
            display_name="Max Speed",
            value=round(v_max_mps, 4),
            unit="m/s",
            source_op_id=None,
            confidence="limit",
        )
    )

    # 5. max_load_factor
    max_turn_marker = markers_by_label.get("max_turn")
    if max_turn_marker is not None:
        kpis.append(
            PerformanceKPI(
                label="max_load_factor",
                display_name="Max Load Factor",
                value=round(max_turn_marker.load_factor, 4),
                unit="g",
                source_op_id=max_turn_marker.op_id,
                confidence="trimmed",
            )
        )
    else:
        kpis.append(
            PerformanceKPI(
                label="max_load_factor",
                display_name="Max Load Factor",
                value=round(g_limit, 4),
                unit="g",
                source_op_id=None,
                confidence="limit",
            )
        )

    # 6. dive_speed
    kpis.append(
        PerformanceKPI(
            label="dive_speed",
            display_name="Dive Speed",
            value=round(1.4 * v_max_mps, 4),
            unit="m/s",
            source_op_id=None,
            confidence="limit",
        )
    )

    return kpis


# ---------------------------------------------------------------------------
# DB-aware helpers
# ---------------------------------------------------------------------------


def _get_aeroplane(db: Session, aeroplane_uuid) -> AeroplaneModel:
    """Query AeroplaneModel by uuid; raise NotFoundError if missing."""
    aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_uuid).first()
    if not aeroplane:
        raise NotFoundError(entity="Aeroplane", resource_id=aeroplane_uuid)
    return aeroplane


def _load_assumptions(db: Session, aeroplane_uuid) -> dict[str, float]:
    """Load effective values for mass, cl_max, g_limit.

    Falls back to PARAMETER_DEFAULTS if a design assumption row is missing.
    """
    from app.services.mass_cg_service import get_effective_assumption_value

    result: dict[str, float] = {}
    for param in ("mass", "cl_max", "g_limit"):
        try:
            result[param] = get_effective_assumption_value(db, aeroplane_uuid, param)
        except NotFoundError:
            result[param] = PARAMETER_DEFAULTS[param]
    return result


def _get_wing_area_m2(db: Session, aeroplane: AeroplaneModel) -> float:
    """Convert aeroplane to ASB Airplane and return s_ref."""
    from app.converters.model_schema_converters import (
        aeroplane_model_to_aeroplane_schema_async,
        aeroplane_schema_to_asb_airplane_async,
    )

    schema = aeroplane_model_to_aeroplane_schema_async(aeroplane)
    asb_airplane = aeroplane_schema_to_asb_airplane_async(schema)
    s_ref = asb_airplane.s_ref
    if s_ref is None or s_ref <= 0:
        raise InternalError("Cannot determine wing reference area — no wings defined")
    return float(s_ref)


def _get_v_max(db: Session, aeroplane: AeroplaneModel) -> float:
    """Get max level speed from flight profile goals; default 28.0 m/s."""
    profile = aeroplane.flight_profile
    if profile is not None:
        goals = profile.goals
        if isinstance(goals, dict):
            v = goals.get("max_level_speed_mps")
            if v is not None:
                return float(v)
    return 28.0


def _load_operating_point_markers(
    db: Session,
    aeroplane: AeroplaneModel,
    mass_kg: float,
    wing_area_m2: float,
) -> list[VnMarker]:
    """Query OperatingPointModel rows for this aeroplane and map to VnMarker."""
    ops = (
        db.query(OperatingPointModel).filter(OperatingPointModel.aircraft_id == aeroplane.id).all()
    )
    markers: list[VnMarker] = []
    for op in ops:
        v = op.velocity
        if v is None or v <= 0:
            continue
        # Operating points represent level flight conditions (n=1.0).
        # Without stored CL, we cannot derive actual load factor.
        n = 1.0
        markers.append(
            VnMarker(
                op_id=op.id,
                name=op.name or "unnamed",
                velocity_mps=v,
                load_factor=round(n, 4),
                status=op.status or "NOT_TRIMMED",
                label=op.name or "unnamed",
            )
        )
    return markers


def _get_b_ref(db: Session, aeroplane: AeroplaneModel) -> float | None:
    """Return wingspan b_ref from the ASB airplane model, or None."""
    from app.converters.model_schema_converters import (
        aeroplane_model_to_aeroplane_schema_async,
        aeroplane_schema_to_asb_airplane_async,
    )

    try:
        schema = aeroplane_model_to_aeroplane_schema_async(aeroplane)
        asb_airplane = aeroplane_schema_to_asb_airplane_async(schema)
        b = asb_airplane.b_ref
        return float(b) if b is not None and b > 0 else None
    except Exception:
        return None


def _model_to_read(row: FlightEnvelopeModel) -> FlightEnvelopeRead:
    """Convert a FlightEnvelopeModel row to a FlightEnvelopeRead schema."""
    vn_curve = VnCurve.model_validate(row.vn_curve_json)
    return FlightEnvelopeRead(
        id=row.id,
        aeroplane_id=row.aeroplane_id,
        vn_curve=vn_curve,
        kpis=[PerformanceKPI.model_validate(k) for k in row.kpis_json],
        operating_points=[VnMarker.model_validate(m) for m in row.markers_json],
        assumptions_snapshot=row.assumptions_snapshot,
        computed_at=row.computed_at,
        # Mirror vn_curve.gust_warnings at the top level for easy frontend access
        gust_warnings=vn_curve.gust_warnings,
    )


# ---------------------------------------------------------------------------
# Public orchestration API
# ---------------------------------------------------------------------------


def compute_flight_envelope(db: Session, aeroplane_uuid) -> FlightEnvelopeRead:
    """Compute (or recompute) the flight envelope for an aeroplane.

    Steps:
    1. Load aeroplane and design assumptions
    2. Get wing area and b_ref via ASB conversion
    3. Get v_max from flight profile
    4. Compute V-n curve (maneuver + gust envelope) and KPIs
    5. Load operating-point markers
    6. Upsert to DB
    7. Return FlightEnvelopeRead

    Gust envelope (gh-487):
      CL_α is read from assumption_computation_context["cl_alpha_per_rad"]
      when available (set by assumption_compute_service after alpha-sweep);
      falls back to Helmbold-Diederich (Anderson 6e Eq. 5.81) otherwise.
      b_ref is taken from the ASB airplane for MGC = S/b computation.
    """
    aeroplane = _get_aeroplane(db, aeroplane_uuid)
    assumptions = _load_assumptions(db, aeroplane_uuid)
    wing_area_m2 = _get_wing_area_m2(db, aeroplane)
    b_ref_m = _get_b_ref(db, aeroplane)
    v_max = _get_v_max(db, aeroplane)

    mass_kg = assumptions["mass"]
    cl_max = assumptions["cl_max"]
    g_limit = assumptions["g_limit"]

    # CL_α for gust computation — prefer context cache, fall back to Helmbold
    ctx = aeroplane.assumption_computation_context or {}
    cl_alpha_per_rad: float | None = _extract_cl_alpha_from_context(ctx)

    vn_curve = compute_vn_curve(
        mass_kg=mass_kg,
        cl_max=cl_max,
        g_limit=g_limit,
        wing_area_m2=wing_area_m2,
        v_max_mps=v_max,
        b_ref_m=b_ref_m,
        cl_alpha_per_rad=cl_alpha_per_rad,
    )

    markers = _load_operating_point_markers(db, aeroplane, mass_kg, wing_area_m2)

    # Pull polar-derived V_md / V_min_sink from the assumption computation
    # context (populated by assumption_compute_service). When present these
    # take precedence over the heuristic 1.4·V_s / 1.2·V_s fallbacks
    # (gh-475 — audit §4.1, off by ~15 % for high-AR airframes).
    v_md_polar = ctx.get("v_md_mps")
    v_min_sink_polar = ctx.get("v_min_sink_mps")

    kpis = derive_performance_kpis(
        stall_speed_mps=vn_curve.stall_speed_mps,
        v_max_mps=v_max,
        g_limit=g_limit,
        markers=markers,
        v_md_polar_mps=float(v_md_polar) if isinstance(v_md_polar, (int, float)) else None,
        v_min_sink_polar_mps=(
            float(v_min_sink_polar) if isinstance(v_min_sink_polar, (int, float)) else None
        ),
    )

    now = datetime.now(timezone.utc)

    # Serialize for JSON columns
    vn_curve_json = vn_curve.model_dump(mode="json")
    kpis_json = [k.model_dump(mode="json") for k in kpis]
    markers_json = [m.model_dump(mode="json") for m in markers]
    assumptions_snapshot = assumptions

    # Upsert: update if exists, create if not
    existing = (
        db.query(FlightEnvelopeModel)
        .filter(FlightEnvelopeModel.aeroplane_id == aeroplane.id)
        .first()
    )
    if existing is not None:
        existing.vn_curve_json = vn_curve_json
        existing.kpis_json = kpis_json
        existing.markers_json = markers_json
        existing.assumptions_snapshot = assumptions_snapshot
        existing.computed_at = now
        db.flush()
        db.refresh(existing)
        return _model_to_read(existing)

    row = FlightEnvelopeModel(
        aeroplane_id=aeroplane.id,
        vn_curve_json=vn_curve_json,
        kpis_json=kpis_json,
        markers_json=markers_json,
        assumptions_snapshot=assumptions_snapshot,
        computed_at=now,
    )
    db.add(row)
    db.flush()
    db.refresh(row)
    return _model_to_read(row)


def get_flight_envelope(db: Session, aeroplane_uuid) -> FlightEnvelopeRead | None:
    """Return the cached flight envelope, or None if not yet computed."""
    aeroplane = _get_aeroplane(db, aeroplane_uuid)
    row = (
        db.query(FlightEnvelopeModel)
        .filter(FlightEnvelopeModel.aeroplane_id == aeroplane.id)
        .first()
    )
    if row is None:
        return None
    return _model_to_read(row)
