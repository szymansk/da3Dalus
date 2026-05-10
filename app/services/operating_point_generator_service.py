import logging
import math
from dataclasses import dataclass
from typing import Any, Optional

import aerosandbox as asb
import numpy as np
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.converters.model_schema_converters import (
    aeroplane_model_to_aeroplane_schema_async,
    aeroplane_schema_to_asb_airplane_async,
)
from app.core.exceptions import InternalError, NotFoundError, ValidationError
from app.models.aeroplanemodel import AeroplaneModel
from app.models.analysismodels import OperatingPointModel, OperatingPointSetModel
from app.models.flightprofilemodel import RCFlightProfileModel
from app.schemas.aeroanalysisschema import (
    GeneratedOperatingPointSetRead,
    OperatingPointStatus,
    StoredOperatingPointCreate,
    StoredOperatingPointRead,
    TrimmedOperatingPointRead,
    TrimOperatingPointRequest,
)
from app.services.trim_enrichment_service import (
    build_deflection_limits_from_schema,
    compute_enrichment,
    parse_role_tag,
)

logger = logging.getLogger(__name__)

PITCH_ROLES = {"elevator", "stabilator", "elevon"}
ROLL_ROLES = {"aileron", "elevon"}
YAW_ROLES = {"rudder"}
FLAP_ROLES = {"flap"}


@dataclass
class TrimmedPoint:
    name: str
    description: str
    config: str
    velocity: float
    altitude: float
    alpha_rad: float
    beta_rad: float
    p: float
    q: float
    r: float
    status: OperatingPointStatus
    warnings: list[str]
    controls: dict[str, float]
    trim_score: float | None = None
    trim_residuals: dict[str, float] | None = None
    trim_method: str = "opti"
    trim_enrichment: dict | None = None


def _safe_coeff(result: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = result.get(key)
    if value is None:
        return default
    if isinstance(value, np.ndarray):
        if value.size == 0:
            return default
        return float(np.ravel(value)[0])
    return float(value)


def _compute_trim_score(cm: float, cy: float, cl: float, cl_target: Optional[float]) -> float:
    score = abs(cm) + 0.5 * abs(cy)
    if cl_target is not None:
        score += 0.3 * abs(cl - cl_target)
    return score


def _default_profile() -> dict[str, Any]:
    return {
        "name": "default_profile",
        "environment": {"altitude_m": 0.0, "wind_mps": 0.0},
        "goals": {
            "cruise_speed_mps": 18.0,
            "max_level_speed_mps": 28.0,
            "min_speed_margin_vs_clean": 1.20,
            "takeoff_speed_margin_vs_to": 1.25,
            "approach_speed_margin_vs_ldg": 1.30,
            "target_turn_n": 2.0,
            "loiter_s": 600,
        },
        "constraints": {"max_alpha_deg": 25.0, "max_beta_deg": 30.0},
    }


def _get_aircraft_or_raise(db: Session, aircraft_uuid) -> AeroplaneModel:
    aircraft = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aircraft_uuid).first()
    if not aircraft:
        raise NotFoundError(entity="Aircraft", resource_id=aircraft_uuid)
    return aircraft


def _get_profile_or_raise(db: Session, profile_id: int) -> RCFlightProfileModel:
    profile = db.query(RCFlightProfileModel).filter(RCFlightProfileModel.id == profile_id).first()
    if not profile:
        raise NotFoundError(entity="RCFlightProfile", resource_id=profile_id)
    return profile


def _load_design_cg_x(db: Session, aeroplane_id: int) -> float:
    """Look up the effective cg_x from design assumptions, or 0.0."""
    from app.models.aeroplanemodel import DesignAssumptionModel

    row = (
        db.query(DesignAssumptionModel)
        .filter(
            DesignAssumptionModel.aeroplane_id == aeroplane_id,
            DesignAssumptionModel.parameter_name == "cg_x",
        )
        .first()
    )
    if row is None:
        return 0.0
    if row.active_source == "CALCULATED" and row.calculated_value is not None:
        return float(row.calculated_value)
    return float(row.estimate_value)


def _load_effective_mass_kg(
    db: Session, aeroplane_id: int, fallback_kg: Optional[float]
) -> Optional[float]:
    """Effective mass from the assumption row, falling back to the
    aeroplane's total_mass_kg field (legacy)."""
    from app.models.aeroplanemodel import DesignAssumptionModel

    row = (
        db.query(DesignAssumptionModel)
        .filter(
            DesignAssumptionModel.aeroplane_id == aeroplane_id,
            DesignAssumptionModel.parameter_name == "mass",
        )
        .first()
    )
    if row is None:
        return fallback_kg
    if row.active_source == "CALCULATED" and row.calculated_value is not None:
        return float(row.calculated_value)
    return float(row.estimate_value)


def _resolve_cruise_speed_with_md_fallback(
    aircraft: AeroplaneModel, goals: dict[str, Any], source_profile_id: Optional[int]
) -> float:
    """When the aircraft has no flight profile, use V_md from the cached
    computation context as the cruise speed. Mirrors the chip behaviour
    in the Info Chip Row."""
    cruise_from_goals = float(goals.get("cruise_speed_mps", 18.0))
    if source_profile_id is not None:
        return cruise_from_goals
    ctx = aircraft.assumption_computation_context or {}
    v_md = ctx.get("v_md_mps")
    if isinstance(v_md, (int, float)) and v_md > 0:
        return float(v_md)
    return cruise_from_goals


def _load_effective_flight_profile(
    db: Session,
    aircraft: AeroplaneModel,
    profile_id_override: Optional[int] = None,
) -> tuple[dict[str, Any], Optional[int]]:
    if profile_id_override is not None:
        profile = _get_profile_or_raise(db, profile_id_override)
        return {
            "name": profile.name,
            "environment": profile.environment,
            "goals": profile.goals,
            "constraints": profile.constraints,
        }, profile.id

    if aircraft.flight_profile_id is not None:
        profile = _get_profile_or_raise(db, aircraft.flight_profile_id)
        return {
            "name": profile.name,
            "environment": profile.environment,
            "goals": profile.goals,
            "constraints": profile.constraints,
        }, profile.id

    return _default_profile(), None


def _estimate_reference_speeds(profile: dict[str, Any]) -> dict[str, float]:
    goals = profile["goals"]
    cruise = float(goals.get("cruise_speed_mps", 18.0))
    min_margin_clean = max(1.05, float(goals.get("min_speed_margin_vs_clean", 1.20)))

    vs_clean = max(3.0, cruise / min_margin_clean)
    vs_to = max(2.5, vs_clean * 0.95)
    vs_ldg = max(2.0, vs_clean * 0.90)

    return {
        "vs_clean": vs_clean,
        "vs_to": vs_to,
        "vs_ldg": vs_ldg,
    }


def _build_target_definitions(
    profile: dict[str, Any], refs: dict[str, float]
) -> list[dict[str, Any]]:
    goals = profile["goals"]
    altitude = float(profile["environment"].get("altitude_m", 0.0))

    cruise = float(goals.get("cruise_speed_mps", 18.0))
    v_max_level = float(goals.get("max_level_speed_mps") or max(1.35 * cruise, cruise + 8.0))
    target_turn_n = float(goals.get("target_turn_n", 2.0))

    stall_near = float(goals.get("min_speed_margin_vs_clean", 1.20)) * refs["vs_clean"]
    takeoff = float(goals.get("takeoff_speed_margin_vs_to", 1.25)) * refs["vs_to"]
    approach = float(goals.get("approach_speed_margin_vs_ldg", 1.30)) * refs["vs_ldg"]

    return [
        {
            "name": "stall_near_clean",
            "config": "clean",
            "velocity": stall_near,
            "altitude": altitude,
            "beta_target_deg": 0.0,
            "n_target": 1.0,
        },
        {
            "name": "takeoff_climb",
            "config": "takeoff",
            "velocity": takeoff,
            "altitude": altitude,
            "beta_target_deg": 0.0,
            "n_target": 1.0,
            "flap_deflection_deg": 15.0,
        },
        {
            "name": "best_angle_climb_vx",
            "config": "clean",
            "velocity": max(1.35 * refs["vs_clean"], cruise * 0.85),
            "altitude": altitude,
            "beta_target_deg": 0.0,
            "n_target": 1.0,
        },
        {
            "name": "best_rate_climb_vy",
            "config": "clean",
            "velocity": max(1.50 * refs["vs_clean"], cruise * 0.95),
            "altitude": altitude,
            "beta_target_deg": 0.0,
            "n_target": 1.0,
        },
        {
            "name": "cruise",
            "config": "clean",
            "velocity": cruise,
            "altitude": altitude,
            "beta_target_deg": 0.0,
            "n_target": 1.0,
        },
        {
            "name": "loiter_endurance",
            "config": "clean",
            "velocity": max(1.15 * refs["vs_clean"], cruise * 0.80),
            "altitude": altitude,
            "beta_target_deg": 0.0,
            "n_target": 1.0,
        },
        {
            "name": "max_range",
            "config": "clean",
            "velocity": max(1.25 * refs["vs_clean"], cruise * 0.95),
            "altitude": altitude,
            "beta_target_deg": 0.0,
            "n_target": 1.0,
        },
        {
            "name": "max_level_speed",
            "config": "clean",
            "velocity": v_max_level,
            "altitude": altitude,
            "beta_target_deg": 0.0,
            "n_target": 1.0,
        },
        {
            "name": "approach_landing",
            "config": "landing",
            "velocity": approach,
            "altitude": altitude,
            "beta_target_deg": 0.0,
            "n_target": 1.0,
            "flap_deflection_deg": 30.0,
        },
        {
            "name": "stall_with_flaps",
            "config": "landing",
            "velocity": max(2.0, refs["vs_ldg"] * 1.05),
            "altitude": altitude,
            "beta_target_deg": 0.0,
            "n_target": 1.0,
            "flap_deflection_deg": 30.0,
        },
        {
            "name": "turn_n2",
            "config": "clean",
            "velocity": max(cruise, 1.3 * refs["vs_clean"]),
            "altitude": altitude,
            "beta_target_deg": 0.0,
            "n_target": target_turn_n,
        },
        {
            "name": "dutch_role_start",
            "config": "clean",
            "velocity": max(cruise, 1.3 * refs["vs_clean"]),
            "altitude": altitude,
            "beta_target_deg": 2.0,
            "n_target": 1.0,
            "warnings": ["NO_CONTROL_TRIM_MVP"],
        },
    ]


def _fallback_speeds(name: str, base_velocity: float) -> list[float]:
    if name == "max_level_speed":
        factors = [1.0, 0.95, 0.90, 0.85]
    else:
        factors = [1.0, 1.05, 1.10, 1.15]
    return [max(2.0, base_velocity * f) for f in factors]


def _pick_control_name(
    available_controls: list[str],
    roles: set[str],
) -> Optional[str]:
    """Find a control surface name whose ``[role]`` tag matches *roles*."""
    for control_name in available_controls:
        role, _display = parse_role_tag(control_name)
        if role and role in roles:
            return control_name
    return None


def _detect_control_capabilities(asb_airplane: asb.Airplane) -> dict[str, Any]:
    control_names: list[str] = []
    roles_found: set[str] = set()

    for wing in getattr(asb_airplane, "wings", []) or []:
        for xsec in getattr(wing, "xsecs", []) or []:
            for cs in getattr(xsec, "control_surfaces", []) or []:
                raw_name = str(getattr(cs, "name", "")).strip()
                if not raw_name:
                    continue
                control_names.append(raw_name)
                role, _display = parse_role_tag(raw_name)
                if role:
                    roles_found.add(role)

    return {
        "has_pitch_control": bool(roles_found & PITCH_ROLES),
        "has_roll_control": bool(roles_found & ROLL_ROLES),
        "has_yaw_control": bool(roles_found & YAW_ROLES),
        "has_flap": bool(roles_found & FLAP_ROLES),
        "available_controls": sorted(set(control_names)),
    }


def _required_capabilities_for_target(target_name: str) -> set[str]:
    if target_name == "turn_n2":
        return {"has_roll_control|has_yaw_control"}
    if target_name == "dutch_role_start":
        return {"has_yaw_control"}
    if target_name == "stall_with_flaps":
        return {"has_flap"}
    return set()


def _validate_target_capability(
    target: dict[str, Any], capabilities: dict[str, Any]
) -> tuple[bool, str]:
    target_name = str(target.get("name", ""))
    if target_name == "turn_n2":
        if capabilities.get("has_roll_control") or capabilities.get("has_yaw_control"):
            return True, ""
        return False, "has_roll_control|has_yaw_control"

    required = _required_capabilities_for_target(target_name)
    missing = sorted(
        capability for capability in required if not capabilities.get(capability, False)
    )
    if missing:
        return False, ",".join(missing)
    return True, ""


def _solve_trim_candidate_with_opti(
    asb_airplane: asb.Airplane,
    target: dict[str, Any],
    velocity_mps: float,
    altitude_m: float,
    beta_target_deg: float,
    cl_target: Optional[float],
    constraints: dict[str, Any],
    capabilities: dict[str, Any],
) -> Optional[dict[str, Any]]:
    try:
        max_alpha = float(constraints.get("max_alpha_deg", 25.0))
        alpha_lower = -8.0
        alpha_upper = max(alpha_lower + 1.0, max_alpha)

        opti = asb.Opti()
        alpha_deg = opti.variable(
            init_guess=min(max(3.0, alpha_lower), alpha_upper),
            lower_bound=alpha_lower,
            upper_bound=alpha_upper,
        )

        available_controls = [
            str(name).strip() for name in capabilities.get("available_controls", [])
        ]
        control_values: dict[str, Any] = {}
        control_variables: dict[str, Any] = {}

        pitch_name = _pick_control_name(available_controls, roles=PITCH_ROLES)
        yaw_name = _pick_control_name(available_controls, roles=YAW_ROLES)
        roll_name = _pick_control_name(available_controls, roles=ROLL_ROLES)

        if pitch_name:
            control_variables[pitch_name] = opti.variable(
                init_guess=0.0, lower_bound=-25.0, upper_bound=25.0
            )
        if target["name"] == "turn_n2" and roll_name:
            control_variables[roll_name] = opti.variable(
                init_guess=0.0, lower_bound=-20.0, upper_bound=20.0
            )
        if target["name"] in {"turn_n2", "dutch_role_start"} and yaw_name:
            control_variables[yaw_name] = opti.variable(
                init_guess=0.0, lower_bound=-25.0, upper_bound=25.0
            )

        if control_variables:
            control_values = dict(control_variables.items())
            # Add fixed flap deflection (not an optimizer variable)
            flap_deflection = target.get("flap_deflection_deg")
            if flap_deflection is not None:
                flap_name = _pick_control_name(available_controls, roles=FLAP_ROLES)
                if flap_name:
                    control_values[flap_name] = float(flap_deflection)
            airplane_for_eval = asb_airplane.with_control_deflections(control_values)
        else:
            # No control variables, but may still have fixed flap deflection
            flap_deflection = target.get("flap_deflection_deg")
            if flap_deflection is not None:
                flap_name = _pick_control_name(available_controls, roles=FLAP_ROLES)
                if flap_name:
                    control_values[flap_name] = float(flap_deflection)
            if control_values:
                airplane_for_eval = asb_airplane.with_control_deflections(control_values)
            else:
                airplane_for_eval = asb_airplane

        op = asb.OperatingPoint(
            velocity=float(velocity_mps),
            alpha=alpha_deg,
            beta=float(beta_target_deg),
            p=0.0,
            q=0.0,
            r=0.0,
            atmosphere=asb.Atmosphere(altitude=altitude_m),
        )

        result = asb.AeroBuildup(
            airplane=airplane_for_eval,
            op_point=op,
            xyz_ref=airplane_for_eval.xyz_ref,
        ).run_with_stability_derivatives()

        cm = result["Cm"]
        cy = result["CY"]
        cl = result["CL"]

        objective = 50.0 * cm**2 + 3.0 * cy**2
        if cl_target is not None:
            objective += 15.0 * (cl - cl_target) ** 2
        if target["name"] == "turn_n2":
            objective += 2.0 * result["Cl"] ** 2 + 2.0 * result["Cn"] ** 2
        for control in control_variables.values():
            objective += 0.001 * control**2

        opti.minimize(objective)
        solution = opti.solve(
            verbose=False,
            max_iter=120,
            max_runtime=0.35,
            behavior_on_failure="return_last",
        )

        solved_alpha = float(solution(alpha_deg))
        solved_cm = float(solution(cm))
        solved_cy = float(solution(cy))
        solved_cl = float(solution(cl))
        solved_controls = {name: float(solution(var)) for name, var in control_variables.items()}

        return {
            "alpha_deg": solved_alpha,
            "beta_deg": float(beta_target_deg),
            "score": _compute_trim_score(solved_cm, solved_cy, solved_cl, cl_target),
            "controls": solved_controls,
            "metrics": {"cm": solved_cm, "cy": solved_cy, "cl": solved_cl},
        }
    except Exception as exc:
        logger.debug("Opti trim candidate failed for %s: %s", target.get("name"), exc)
        return None


def _evaluate_trim_candidate(
    asb_airplane: asb.Airplane,
    altitude_m: float,
    velocity_mps: float,
    alpha_deg: float,
    beta_deg: float,
    cl_target: Optional[float],
    controls: Optional[dict[str, float]] = None,
) -> tuple[float, dict[str, float]]:
    atmosphere = asb.Atmosphere(altitude=altitude_m)
    op = asb.OperatingPoint(
        velocity=float(velocity_mps),
        alpha=float(alpha_deg),
        beta=float(beta_deg),
        p=0.0,
        q=0.0,
        r=0.0,
        atmosphere=atmosphere,
    )

    airplane_for_eval = (
        asb_airplane.with_control_deflections(controls) if controls else asb_airplane
    )
    result = asb.AeroBuildup(
        airplane=airplane_for_eval,
        op_point=op,
        xyz_ref=airplane_for_eval.xyz_ref,
    ).run_with_stability_derivatives()

    cm = _safe_coeff(result, "Cm")
    cl = _safe_coeff(result, "CL")
    cy = _safe_coeff(result, "CY")

    score = _compute_trim_score(cm, cy, cl, cl_target)

    return score, {"cm": cm, "cl": cl, "cy": cy}


def _cl_target_for_velocity(
    candidate_velocity_mps: float,
    total_mass_kg: Optional[float],
    s_ref: float,
    rho: float,
    n_target: float,
) -> Optional[float]:
    """Compute the CL target for a given velocity, or None if not computable."""
    if not total_mass_kg or s_ref <= 0:
        return None
    q_dyn = 0.5 * rho * max(candidate_velocity_mps, 1e-3) ** 2
    if q_dyn <= 1e-6:
        return None
    return float((total_mass_kg * 9.81 * n_target) / (q_dyn * s_ref))


def _grid_search_trim(
    asb_airplane: asb.Airplane,
    target: dict[str, Any],
    velocity: float,
    altitude: float,
    beta_candidates: list[float],
    cl_target_fn,
) -> tuple[float, float, float, float, dict[str, float]]:
    """Run a grid search over velocities, alphas, and betas to find the best trim.

    Returns (best_score, best_alpha, best_beta, velocity, best_controls).
    """
    best_score = float("inf")
    best_alpha = 0.0
    best_beta = beta_candidates[0]
    best_velocity = velocity
    best_controls: dict[str, float] = {}

    for candidate_velocity in _fallback_speeds(target["name"], velocity):
        alpha_candidates = np.linspace(-4.0, 20.0, 13)
        for beta_deg in beta_candidates:
            for alpha_deg in alpha_candidates:
                try:
                    score, _ = _evaluate_trim_candidate(
                        asb_airplane=asb_airplane,
                        altitude_m=altitude,
                        velocity_mps=candidate_velocity,
                        alpha_deg=float(alpha_deg),
                        beta_deg=float(beta_deg),
                        cl_target=cl_target_fn(candidate_velocity),
                    )
                except Exception as exc:
                    logger.debug("Trim candidate failed for %s: %s", target["name"], exc)
                    continue

                if score < best_score:
                    best_score = score
                    best_alpha = float(alpha_deg)
                    best_beta = float(beta_deg)
                    best_velocity = candidate_velocity
                    best_controls = {}

    return best_score, best_alpha, best_beta, best_velocity, best_controls


def _apply_limit_warnings(
    best_alpha: float,
    best_beta: float,
    best_score: float,
    constraints: dict[str, Any],
    warnings: list[str],
) -> OperatingPointStatus:
    """Determine trim status and append limit-reached warnings."""
    trim_status = (
        OperatingPointStatus.TRIMMED if best_score < 0.35 else OperatingPointStatus.NOT_TRIMMED
    )
    if trim_status == OperatingPointStatus.NOT_TRIMMED:
        warnings.append("NOT_TRIMMED")

    max_alpha = constraints.get("max_alpha_deg")
    if max_alpha is not None and abs(best_alpha) > float(max_alpha):
        trim_status = OperatingPointStatus.LIMIT_REACHED
        warnings.append("ALPHA_LIMIT_REACHED")

    max_beta = constraints.get("max_beta_deg")
    if max_beta is not None and abs(best_beta) > float(max_beta):
        trim_status = OperatingPointStatus.LIMIT_REACHED
        warnings.append("BETA_LIMIT_REACHED")

    return trim_status


def _trim_or_estimate_point(
    asb_airplane: asb.Airplane,
    aircraft: AeroplaneModel,
    target: dict[str, Any],
    constraints: dict[str, Any],
    capabilities: dict[str, Any],
    effective_mass_kg: Optional[float] = None,
) -> TrimmedPoint:
    warnings = list(target.get("warnings", []))
    velocity = float(target["velocity"])
    altitude = float(target["altitude"])

    rho = float(asb.Atmosphere(altitude=altitude).density())
    s_ref = float(getattr(asb_airplane, "s_ref", 0.0) or 0.0)
    n_target = float(target.get("n_target", 1.0))
    # Effective mass from the design assumptions takes precedence over
    # the legacy aircraft.total_mass_kg field — that way Component-Tree
    # weight changes (which sync into the mass assumption) flow into
    # CL_target without requiring a separate aircraft-level update.
    mass_for_cl = (
        effective_mass_kg if effective_mass_kg is not None else aircraft.total_mass_kg
    )

    def cl_target_fn(v: float) -> Optional[float]:
        return _cl_target_for_velocity(v, mass_for_cl, s_ref, rho, n_target)

    beta_candidates = [float(target.get("beta_target_deg", 0.0))]
    if target["name"] == "dutch_role_start":
        beta_candidates += [0.0, -2.0]

    # Run Opti once on the nominal target
    best_score = float("inf")
    best_alpha = 0.0
    best_beta = beta_candidates[0]
    best_controls: dict[str, float] = {}
    best_residuals: dict[str, float] = {}
    best_method = "opti"

    opti_solution = _solve_trim_candidate_with_opti(
        asb_airplane=asb_airplane,
        target=target,
        velocity_mps=velocity,
        altitude_m=altitude,
        beta_target_deg=float(beta_candidates[0]),
        cl_target=cl_target_fn(velocity),
        constraints=constraints,
        capabilities=capabilities,
    )
    if opti_solution and opti_solution["score"] < best_score:
        best_score = float(opti_solution["score"])
        best_alpha = float(opti_solution["alpha_deg"])
        best_beta = float(opti_solution["beta_deg"])
        best_controls = dict(opti_solution["controls"])
        best_residuals = dict(opti_solution.get("metrics", {}))
        best_method = "opti"

    # Fallback grid-search if opti didn't converge well enough
    if best_score > 0.35:
        gs_score, gs_alpha, gs_beta, gs_velocity, gs_controls = _grid_search_trim(
            asb_airplane,
            target,
            velocity,
            altitude,
            beta_candidates,
            cl_target_fn,
        )
        if gs_score < best_score:
            best_score, best_alpha, best_beta, best_controls = (
                gs_score,
                gs_alpha,
                gs_beta,
                gs_controls,
            )
            best_residuals = {}
            best_method = "grid_search"
            velocity = gs_velocity

    trim_status = _apply_limit_warnings(best_alpha, best_beta, best_score, constraints, warnings)

    return TrimmedPoint(
        name=target["name"],
        description=(
            f"config={target['config']}, target_n={target.get('n_target', 1.0):.2f}, "
            f"V={velocity:.2f}mps, altitude={altitude:.1f}m"
        ),
        config=target["config"],
        velocity=float(velocity),
        altitude=float(altitude),
        alpha_rad=math.radians(best_alpha),
        beta_rad=math.radians(best_beta),
        p=0.0,
        q=0.0,
        r=0.0,
        status=trim_status,
        warnings=warnings,
        controls=best_controls,
        trim_score=best_score if best_score < float("inf") else None,
        trim_residuals=best_residuals,
        trim_method=best_method,
    )


def _persist_point_set(
    db: Session,
    aircraft: AeroplaneModel,
    points: list[TrimmedPoint],
    source_flight_profile_id: Optional[int],
    replace_existing: bool,
    design_cg_x: float = 0.0,
) -> tuple[OperatingPointSetModel, list[OperatingPointModel]]:
    if replace_existing:
        db.query(OperatingPointSetModel).filter(
            OperatingPointSetModel.aircraft_id == aircraft.id
        ).delete(synchronize_session=False)
        db.query(OperatingPointModel).filter(OperatingPointModel.aircraft_id == aircraft.id).delete(
            synchronize_session=False
        )

    stored_points: list[OperatingPointModel] = []
    for point in points:
        model = OperatingPointModel(
            aircraft_id=aircraft.id,
            name=point.name,
            description=point.description,
            config=point.config,
            status=point.status.value,
            warnings=point.warnings,
            controls=point.controls,
            velocity=point.velocity,
            alpha=point.alpha_rad,
            beta=point.beta_rad,
            p=point.p,
            q=point.q,
            r=point.r,
            xyz_ref=[design_cg_x, 0.0, 0.0],
            altitude=point.altitude,
            trim_enrichment=point.trim_enrichment,
        )
        db.add(model)
        stored_points.append(model)

    db.flush()

    opset = OperatingPointSetModel(
        name="default_operating_point_set",
        description="Auto-generated standard operating point set including Dutch-roll start point.",
        aircraft_id=aircraft.id,
        source_flight_profile_id=source_flight_profile_id,
        operating_points=[point.id for point in stored_points],
    )
    db.add(opset)
    db.flush()

    return opset, stored_points


def generate_default_set_for_aircraft(
    db: Session,
    aircraft_uuid,
    replace_existing: bool = False,
    profile_id_override: Optional[int] = None,
) -> GeneratedOperatingPointSetRead:
    try:
        aircraft = _get_aircraft_or_raise(db, aircraft_uuid)
        profile, source_profile_id = _load_effective_flight_profile(
            db, aircraft, profile_id_override
        )
        # When no flight profile is set, fall back to V_md for cruise —
        # the same auto-suggestion logic the Info Chip Row uses. Patch
        # the goals dict in-place before reference-speed estimation so
        # all downstream targets see the resolved cruise speed.
        cruise_resolved = _resolve_cruise_speed_with_md_fallback(
            aircraft, profile.get("goals", {}), source_profile_id
        )
        profile.setdefault("goals", {})["cruise_speed_mps"] = cruise_resolved

        # Effective values from design assumptions take precedence over
        # legacy aircraft fields, so Component-Tree weight changes and
        # SM choices flow into the trim solution without an extra step.
        effective_mass_kg = _load_effective_mass_kg(
            db, aircraft.id, aircraft.total_mass_kg
        )
        design_cg_x = _load_design_cg_x(db, aircraft.id)

        refs = _estimate_reference_speeds(profile)
        targets = _build_target_definitions(profile, refs)

        plane_schema = aeroplane_model_to_aeroplane_schema_async(aircraft)
        asb_airplane = aeroplane_schema_to_asb_airplane_async(plane_schema=plane_schema)
        # Use the design CG as the moment-reference point for trim, so
        # Cm=0 means "balanced about the user's design CG", not about
        # the origin. Mirrors what stability_summary already does.
        asb_airplane.xyz_ref = [design_cg_x, 0.0, 0.0]
        capabilities = _detect_control_capabilities(asb_airplane)
        deflection_limits = build_deflection_limits_from_schema(plane_schema)

        points: list[TrimmedPoint] = []
        skipped_names: list[str] = []
        for target in targets:
            is_supported, missing_required = _validate_target_capability(target, capabilities)
            if not is_supported:
                skipped_names.append(target["name"])
                logger.warning(
                    "Skipping operating point '%s' for aircraft %s: missing required controls=%s, available=%s",
                    target["name"],
                    aircraft_uuid,
                    missing_required,
                    capabilities.get("available_controls", []),
                )
                continue

            point = _trim_or_estimate_point(
                asb_airplane=asb_airplane,
                aircraft=aircraft,
                target=target,
                constraints=profile.get("constraints", {}),
                capabilities=capabilities,
                effective_mass_kg=effective_mass_kg,
            )
            try:
                enrichment = compute_enrichment(
                    controls=point.controls,
                    limits=deflection_limits,
                    trim_method=point.trim_method,
                    trim_score=point.trim_score,
                    trim_residuals=point.trim_residuals or {},
                    op_name=point.name,
                    alpha_deg=math.degrees(point.alpha_rad),
                    status=point.status.value if point.status else None,
                )
                point.trim_enrichment = enrichment.model_dump()
            except Exception:
                logger.warning(
                    "Enrichment computation failed for OP '%s' on aircraft %s",
                    point.name,
                    aircraft_uuid,
                    exc_info=True,
                )
            points.append(point)

        logger.info(
            "Operating-point generation finished for aircraft %s: generated=%d, skipped=%d, skipped_names=%s",
            aircraft_uuid,
            len(points),
            len(skipped_names),
            skipped_names,
        )

        opset, stored_points = _persist_point_set(
            db=db,
            aircraft=aircraft,
            points=points,
            source_flight_profile_id=source_profile_id,
            replace_existing=replace_existing,
            design_cg_x=design_cg_x,
        )

        db.flush()
        db.refresh(opset)
        for point in stored_points:
            db.refresh(point)

        return GeneratedOperatingPointSetRead(
            id=opset.id,
            name=opset.name,
            description=opset.description,
            aircraft_id=opset.aircraft_id,
            source_flight_profile_id=opset.source_flight_profile_id,
            operating_points=[
                StoredOperatingPointRead.model_validate(point, from_attributes=True)
                for point in stored_points
            ],
        )
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as exc:
        raise InternalError(f"Database error: {exc}")
    except Exception as exc:
        raise InternalError(f"Operating-point generation error: {exc}")


def trim_operating_point_for_aircraft(
    db: Session,
    aircraft_uuid,
    request: TrimOperatingPointRequest,
) -> TrimmedOperatingPointRead:
    try:
        aircraft = _get_aircraft_or_raise(db, aircraft_uuid)
        profile, source_profile_id = _load_effective_flight_profile(
            db,
            aircraft,
            request.profile_id_override,
        )

        plane_schema = aeroplane_model_to_aeroplane_schema_async(aircraft)
        asb_airplane = aeroplane_schema_to_asb_airplane_async(plane_schema=plane_schema)
        capabilities = _detect_control_capabilities(asb_airplane)

        target = {
            "name": request.name,
            "config": request.config,
            "velocity": float(request.velocity),
            "altitude": float(request.altitude),
            "beta_target_deg": float(request.beta_target_deg),
            "n_target": float(request.n_target),
            "warnings": list(request.warnings),
        }

        is_supported, missing_required = _validate_target_capability(target, capabilities)
        if not is_supported:
            raise ValidationError(
                message=f"Operating point '{request.name}' cannot be trimmed with the available controls.",
                details={
                    "name": request.name,
                    "missing_required_controls": missing_required,
                    "available_controls": capabilities.get("available_controls", []),
                },
            )

        effective_mass_kg = _load_effective_mass_kg(
            db, aircraft.id, aircraft.total_mass_kg
        )
        design_cg_x = _load_design_cg_x(db, aircraft.id)

        point = _trim_or_estimate_point(
            asb_airplane=asb_airplane,
            aircraft=aircraft,
            target=target,
            constraints=profile.get("constraints", {}),
            capabilities=capabilities,
            effective_mass_kg=effective_mass_kg,
        )

        deflection_limits = build_deflection_limits_from_schema(plane_schema)
        enrichment_data = None
        try:
            enrichment = compute_enrichment(
                controls=point.controls,
                limits=deflection_limits,
                trim_method=point.trim_method,
                trim_score=point.trim_score,
                trim_residuals=point.trim_residuals or {},
                op_name=point.name,
                alpha_deg=math.degrees(point.alpha_rad),
                status=point.status.value if point.status else None,
            )
            enrichment_data = enrichment.model_dump()
        except Exception:
            logger.warning(
                "Enrichment computation failed for single trim OP '%s' on aircraft %s",
                point.name,
                aircraft_uuid,
                exc_info=True,
            )

        point_payload = StoredOperatingPointCreate(
            name=point.name,
            description=point.description,
            aircraft_id=aircraft.id,
            config=point.config,
            status=point.status,
            warnings=point.warnings,
            controls=point.controls,
            velocity=point.velocity,
            alpha=point.alpha_rad,
            beta=point.beta_rad,
            p=point.p,
            q=point.q,
            r=point.r,
            xyz_ref=[design_cg_x, 0.0, 0.0],
            altitude=point.altitude,
            trim_enrichment=enrichment_data,
        )
        return TrimmedOperatingPointRead(
            source_flight_profile_id=source_profile_id,
            point=point_payload,
        )
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as exc:
        raise InternalError(f"Database error: {exc}")
    except Exception as exc:
        raise InternalError(f"Operating-point trim error: {exc}")
