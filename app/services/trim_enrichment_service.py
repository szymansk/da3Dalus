"""Trim result enrichment — deflection reserve, effectiveness, stability, warnings.

Centralises all enrichment computation for trim results across all three
trim paths (opti, AVL, AeroBuildup).  Extracted from
``operating_point_generator_service`` so that every solver can call a
single ``compute_enrichment()`` entry point.
"""

from __future__ import annotations

import re
from typing import Any

from app.schemas.aeroanalysisschema import (
    ControlEffectiveness,
    DeflectionReserve,
    DesignWarning,
    MixerValues,
    OperatingPointStatus,
    StabilityClassification,
    TrimEnrichment,
)

_ROLE_TAG_RE = re.compile(r"^\[(\w+)\](.*)$")

DUAL_ROLES = {"elevon", "flaperon", "ruddervator"}

# Role -> primary coefficient mapping
ROLE_COEFFICIENT_MAP: dict[str, str] = {
    "elevator": "Cm",
    "stabilator": "Cm",
    "aileron": "Cl",
    "rudder": "Cn",
    "elevon": "Cm",       # dual-role: pitch is primary, roll via differential
    "flaperon": "Cl",     # dual-role: roll is primary, flap (lift) via symmetric
    "ruddervator": "Cm",  # V-tail: pitch is primary, yaw via differential
    "flap": "CL",
}

ANALYSIS_GOALS: dict[str, str] = {
    "stall_near_clean": "Can the aircraft trim near stall? How much elevator authority remains?",
    "takeoff_climb": "What flap + elevator setting gives safe climb at takeoff speed?",
    "cruise": "What is the drag-minimal trim at cruise speed?",
    "loiter_endurance": "What trim gives minimum sink for max loiter endurance?",
    "max_level_speed": "Can the aircraft trim at Vmax? Is the tail adequate?",
    "approach_landing": "What flap + elevator trim for safe approach speed?",
    "turn_n2": "How much aileron + rudder for coordinated turn at 2g?",
    "dutch_role_start": "How does the aircraft respond to sideslip? Is yaw damping adequate?",
    "best_angle_climb_vx": "What trim gives the steepest climb for obstacle clearance?",
    "best_rate_climb_vy": "What trim gives the fastest altitude gain?",
    "max_range": "What trim maximizes ground distance per unit energy?",
    "stall_with_flaps": "How does stall behavior change with flaps deployed?",
}

_DEFAULT_ANALYSIS_GOAL = "User-defined trim point"


def parse_role_tag(name: str) -> tuple[str | None, str]:
    """Parse a ``[role]display`` tag from a control surface name.

    Returns ``(role, display)`` when the tag is present, otherwise
    ``(None, name)``.
    """
    m = _ROLE_TAG_RE.match(name)
    if m:
        return m.group(1), m.group(2)
    return None, name


def build_deflection_limits_from_schema(
    plane_schema: Any,
) -> dict[str, tuple[float, float]]:
    """Extract per-surface mechanical limits from plane schema TEDs.

    Returns dict mapping control surface name (with [role] tag) to
    ``(max_pos_deg, max_neg_deg)``.  Falls back to ``(25.0, 25.0)``
    if TED limits are not set.
    """
    default = 25.0
    limits: dict[str, tuple[float, float]] = {}

    if not plane_schema or not getattr(plane_schema, "wings", None):
        return limits

    wings = plane_schema.wings
    if isinstance(wings, dict):
        wing_list = list(wings.values())
    else:
        wing_list = list(wings) if wings else []

    for wing in wing_list:
        xsecs = getattr(wing, "x_secs", None) or getattr(wing, "xsecs", None) or []
        if isinstance(xsecs, dict):
            xsec_list = list(xsecs.values())
        else:
            xsec_list = list(xsecs) if xsecs else []

        for xsec in xsec_list:
            ted = getattr(xsec, "trailing_edge_device", None)
            if ted is None:
                continue

            name = getattr(ted, "name", None)
            if not name:
                continue
            name = str(name).strip()
            if not name:
                continue

            pos = getattr(ted, "positive_deflection_deg", None)
            neg = getattr(ted, "negative_deflection_deg", None)
            max_pos = float(pos) if pos is not None else default
            max_neg = float(neg) if neg is not None else default
            limits[name] = (max_pos, max_neg)

    return limits


def classify_stability(
    stability_derivatives: dict[str, float],
) -> StabilityClassification:
    """Classify static stability from derivatives at the trim point.

    Only classifies based on derivatives that are actually present.
    Missing derivatives are assumed stable (not counted against the
    aircraft), but prevent a full "stable" classification — the result
    is "neutral" when some axes are unknown.
    """
    has_cm_a = "Cm_a" in stability_derivatives
    has_cn_b = "Cn_b" in stability_derivatives or "Cnb" in stability_derivatives
    has_cl_b = "Cl_b" in stability_derivatives or "Clb" in stability_derivatives

    cm_a = stability_derivatives.get("Cm_a", 0.0)
    cn_b = stability_derivatives.get("Cn_b", stability_derivatives.get("Cnb", 0.0))
    cl_b = stability_derivatives.get("Cl_b", stability_derivatives.get("Clb", 0.0))
    cl_a = stability_derivatives.get("CL_a", 0.0)

    is_static = cm_a < 0 if has_cm_a else True
    is_directional = cn_b > 0 if has_cn_b else True
    is_lateral = cl_b < 0 if has_cl_b else True

    static_margin: float | None = None
    if has_cm_a and abs(cl_a) > 1e-6:
        static_margin = round(-cm_a / cl_a, 4)

    # Classify based on KNOWN derivatives only
    known_axes_stable: list[bool] = []
    if has_cm_a:
        known_axes_stable.append(is_static)
    if has_cn_b:
        known_axes_stable.append(is_directional)
    if has_cl_b:
        known_axes_stable.append(is_lateral)

    if not known_axes_stable:
        overall = "neutral"  # no data
    elif all(known_axes_stable):
        if len(known_axes_stable) == 3:
            overall = "stable"
        else:
            overall = "neutral"  # partially stable but not fully confirmed
    else:
        overall = "unstable"  # at least one known axis is unstable

    return StabilityClassification(
        is_statically_stable=is_static,
        is_directionally_stable=is_directional,
        is_laterally_stable=is_lateral,
        static_margin=static_margin,
        overall_class=overall,
    )


def compute_control_effectiveness(
    stability_derivatives: dict[str, float],
    controls: dict[str, float],
) -> dict[str, ControlEffectiveness]:
    """Extract per-surface control effectiveness from stability derivatives.

    For AVL, raw results contain control derivatives like ``Cmd1``, ``Cld1`` etc.
    For the opti/AeroBuildup path, we use state derivatives as a proxy for
    control effectiveness since direct control derivatives aren't available.
    """
    effectiveness: dict[str, ControlEffectiveness] = {}

    # Map role -> state derivative as fallback
    _state_deriv_map: dict[str, str] = {
        "Cm": "Cm_a",
        "Cl": "Cl_b",
        "Cn": "Cn_b",
        "CL": "CL_a",
    }

    for surface_name in controls:
        role, _display = parse_role_tag(surface_name)
        if not role:
            continue

        coeff = ROLE_COEFFICIENT_MAP.get(role)
        if not coeff:
            continue

        # Try to find the state derivative for the relevant axis
        state_key = _state_deriv_map.get(coeff)
        deriv_value: float | None = None
        if state_key and state_key in stability_derivatives:
            deriv_value = stability_derivatives[state_key]

        if deriv_value is not None:
            effectiveness[surface_name] = ControlEffectiveness(
                derivative=round(float(deriv_value), 6),
                coefficient=coeff,
                surface=surface_name,
            )

    return effectiveness


def decompose_dual_role(
    controls: dict[str, float],
) -> dict[str, MixerValues]:
    """Decompose dual-role surface deflections into symmetric and differential components.

    Looks for paired surfaces with the same dual-role tag
    (e.g. two ``[elevon]`` surfaces).
    Symmetric = average, Differential = half the difference.
    """
    mixer_values: dict[str, MixerValues] = {}

    # Group controls by role
    role_groups: dict[str, list[tuple[str, float]]] = {}
    for surface_name, deflection in controls.items():
        role, _display = parse_role_tag(surface_name)
        if role and role in DUAL_ROLES:
            role_groups.setdefault(role, []).append((surface_name, deflection))

    for role, surfaces in role_groups.items():
        if len(surfaces) >= 2:
            # Paired surfaces: compute symmetric and differential
            defl_values = [d for _, d in surfaces]
            symmetric = sum(defl_values) / len(defl_values)
            # Differential = half-difference between first two surfaces
            differential = abs(defl_values[0] - defl_values[1]) / 2.0
            group_key = f"{role}_mixer"
            mixer_values[group_key] = MixerValues(
                symmetric_offset=round(symmetric, 3),
                differential_throw=round(differential, 3),
                role=role,
            )
        elif len(surfaces) == 1:
            # Single dual-role surface: symmetric = deflection, differential = 0
            name, deflection = surfaces[0]
            mixer_values[name] = MixerValues(
                symmetric_offset=round(deflection, 3),
                differential_throw=0.0,
                role=role,
            )

    return mixer_values


def generate_result_summary(
    op_name: str,
    alpha_deg: float,
    controls: dict[str, float],
    deflection_reserves: dict[str, DeflectionReserve],
    stability_class: StabilityClassification | None,
    aero_coefficients: dict[str, float] | None = None,
) -> str:
    """Generate a human-readable result summary for a trim point."""
    alpha_str = f"alpha={alpha_deg:.1f}deg"

    # Find the main pitch control and its reserve
    pitch_reserve_str = ""
    for name, reserve in deflection_reserves.items():
        role, _ = parse_role_tag(name)
        if role in ("elevator", "stabilator", "elevon", "ruddervator"):
            reserve_pct = (1 - reserve.usage_fraction) * 100
            pitch_reserve_str = f" with {reserve_pct:.0f}% elevator reserve"
            break

    cl_str = ""
    if aero_coefficients and "CL" in aero_coefficients:
        cl_str = f", CL={aero_coefficients['CL']:.3f}"

    stability_str = ""
    if stability_class:
        stability_str = f" ({stability_class.overall_class})"

    summaries: dict[str, str] = {
        "stall_near_clean": f"Trimmed at {alpha_str}{pitch_reserve_str}{stability_str}",
        "cruise": f"Drag-minimal trim at {alpha_str}{cl_str}{pitch_reserve_str}{stability_str}",
        "takeoff_climb": f"Takeoff trim at {alpha_str}{pitch_reserve_str}",
        "loiter_endurance": f"Loiter trim at {alpha_str}{cl_str}{pitch_reserve_str}",
        "max_level_speed": f"Max-speed trim at {alpha_str}{pitch_reserve_str}{stability_str}",
        "approach_landing": f"Approach trim at {alpha_str}{pitch_reserve_str}",
        "turn_n2": f"2g turn trim at {alpha_str}{pitch_reserve_str}",
        "dutch_role_start": f"Dutch roll initial condition at {alpha_str}{stability_str}",
        "best_angle_climb_vx": f"Best angle climb at {alpha_str}{pitch_reserve_str}",
        "best_rate_climb_vy": f"Best rate climb at {alpha_str}{pitch_reserve_str}",
        "max_range": f"Max range trim at {alpha_str}{cl_str}{pitch_reserve_str}",
        "stall_with_flaps": f"Flaps-down stall at {alpha_str}{pitch_reserve_str}",
    }

    return summaries.get(op_name, f"Trimmed at {alpha_str}{pitch_reserve_str}{stability_str}")


def compute_enrichment(
    controls: dict[str, float],
    limits: dict[str, tuple[float, float]],
    trim_method: str,
    trim_score: float | None,
    trim_residuals: dict[str, float],
    op_name: str,
    alpha_deg: float,
    stability_derivatives: dict[str, float] | None = None,
    aero_coefficients: dict[str, float] | None = None,
    status: str | None = None,
    reserve_warning_threshold: float = 0.80,
    reserve_critical_threshold: float = 0.95,
    margin_low_threshold: float = 0.05,
    margin_high_threshold: float = 0.30,
) -> TrimEnrichment:
    """Compute full enrichment from trim results.

    This is the single entry point for all enrichment computation,
    used by all three trim paths (opti, AVL, AeroBuildup).
    """
    analysis_goal = ANALYSIS_GOALS.get(op_name, _DEFAULT_ANALYSIS_GOAL)

    # --- Deflection reserves ---
    deflection_reserves: dict[str, DeflectionReserve] = {}
    for surface_name, deflection_deg in controls.items():
        max_pos, max_neg = limits.get(surface_name, (25.0, 25.0))
        limit = max_pos if deflection_deg >= 0 else max_neg
        usage = abs(deflection_deg) / limit if limit > 0 else 0.0
        deflection_reserves[surface_name] = DeflectionReserve(
            deflection_deg=deflection_deg,
            max_pos_deg=max_pos,
            max_neg_deg=max_neg,
            usage_fraction=usage,
        )

    # --- Design warnings ---
    warnings: list[DesignWarning] = []
    for surface_name, reserve in deflection_reserves.items():
        if reserve.usage_fraction > reserve_critical_threshold:
            warnings.append(
                DesignWarning(
                    level="critical",
                    category="authority",
                    surface=surface_name,
                    message=(
                        f"{surface_name}: near mechanical limit "
                        f"({reserve.usage_fraction:.0%} used) — redesign needed"
                    ),
                )
            )
        elif reserve.usage_fraction > reserve_warning_threshold:
            warnings.append(
                DesignWarning(
                    level="warning",
                    category="authority",
                    surface=surface_name,
                    message=(
                        f"{surface_name}: {reserve.usage_fraction:.0%} authority used "
                        f"— surface may be undersized"
                    ),
                )
            )

    if trim_score is not None:
        if trim_score > 0.5:
            warnings.append(
                DesignWarning(
                    level="critical",
                    category="trim_quality",
                    surface=None,
                    message="Trim failed to converge — results unreliable",
                )
            )
        elif trim_score > 0.1:
            warnings.append(
                DesignWarning(
                    level="warning",
                    category="trim_quality",
                    surface=None,
                    message="Poor trim quality — equilibrium not fully achieved",
                )
            )

    if status == OperatingPointStatus.LIMIT_REACHED:
        warnings.append(
            DesignWarning(
                level="critical",
                category="authority",
                surface=None,
                message="Optimizer hit a constraint boundary — check all surfaces",
            )
        )

    # --- Stability classification ---
    stability_classification: StabilityClassification | None = None
    if stability_derivatives:
        stability_classification = classify_stability(stability_derivatives)

        # Static margin warnings
        if stability_classification.static_margin is not None:
            sm = stability_classification.static_margin
            if sm <= 0:
                warnings.append(
                    DesignWarning(
                        level="critical",
                        category="stability",
                        surface=None,
                        message=(
                            f"Negative static margin ({sm:.1%}) — aircraft is statically unstable"
                        ),
                    )
                )
            elif sm < margin_low_threshold:
                warnings.append(
                    DesignWarning(
                        level="warning",
                        category="stability",
                        surface=None,
                        message=(
                            f"Marginal static margin ({sm:.1%}) at this trim point "
                            f"— consider moving CG forward"
                        ),
                    )
                )
            elif sm > margin_high_threshold:
                warnings.append(
                    DesignWarning(
                        level="warning",
                        category="stability",
                        surface=None,
                        message=(
                            f"Very nose-heavy trim (static margin {sm:.1%}) "
                            f"— excessive elevator authority needed"
                        ),
                    )
                )

    # --- Control effectiveness ---
    effectiveness: dict[str, ControlEffectiveness] = {}
    if stability_derivatives:
        effectiveness = compute_control_effectiveness(stability_derivatives, controls)

    # --- Dual-role decomposition ---
    mixer_values = decompose_dual_role(controls)

    # --- Result summary ---
    result_summary = generate_result_summary(
        op_name=op_name,
        alpha_deg=alpha_deg,
        controls=controls,
        deflection_reserves=deflection_reserves,
        stability_class=stability_classification,
        aero_coefficients=aero_coefficients,
    )

    return TrimEnrichment(
        analysis_goal=analysis_goal,
        trim_method=trim_method,
        trim_score=trim_score,
        trim_residuals=trim_residuals,
        deflection_reserves=deflection_reserves,
        design_warnings=warnings,
        effectiveness=effectiveness,
        stability_classification=stability_classification,
        mixer_values=mixer_values,
        result_summary=result_summary,
        aero_coefficients=aero_coefficients or {},
    )
