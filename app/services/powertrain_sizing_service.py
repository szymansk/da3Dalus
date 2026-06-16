"""Powertrain Sizing Service — recommend motor+ESC+battery combos for a mission.

Refactored for gh-490 (Model A): the catalog sweep logic is preserved, but the
power-required physics are now delegated to endurance_service._power_required
instead of relying on hardcoded geometry constants.

gh-960: when aerodynamic parameters (cd0, e_oswald, AR, S_ref) are not supplied
in the request, the service now:
  1. Prefers values from the aeroplane's assumption_computation_context
     (single source of truth, gh-924).
  2. Falls back to RC-typical defaults when neither request nor context provides
     a value, and appends a descriptive warning to the response.
"""

from __future__ import annotations

import logging
import math
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.aeroplanemodel import AeroplaneModel
from app.models.component import ComponentModel
from app.schemas.powertrain_sizing import (
    PowertrainCandidate,
    PowertrainSizingRequest,
    PowertrainSizingResponse,
)
from app.services.endurance_service import (
    DEFAULT_ETA_ESC,
    DEFAULT_ETA_MOTOR,
    DEFAULT_ETA_PROP,
    RHO_SEA_LEVEL,
    _power_required,
)

logger = logging.getLogger(__name__)

AIR_DENSITY_SEA_LEVEL = RHO_SEA_LEVEL  # kept for backward compat with existing tests

# RC-typical defaults used when neither request nor aeroplane context provides a value.
_DEFAULT_CD0 = 0.03
_DEFAULT_E_OSWALD = 0.8
_DEFAULT_AR = 8.0
_DEFAULT_S_REF_M2 = 0.5


def _air_density(altitude_m: float) -> float:
    """ISA air density approximation."""
    return RHO_SEA_LEVEL * math.exp(-altitude_m / 8500.0)


def _required_power_w(speed_ms: float, total_mass_kg: float, altitude_m: float) -> float:
    """Legacy shim — removed in gh-490 (Model A refactor).

    This function no longer accepts requests without aircraft geometry.
    Call _combo_required_power_w with explicit cd0, e_oswald, ar, s_ref_m2,
    and eta_total derived from the actual aircraft or powertrain sizing request.

    Raises
    ------
    NotImplementedError always — powertrain_sizing_service requires aircraft
    geometry; legacy estimate-only mode removed in gh-490.
    """
    raise NotImplementedError(
        "powertrain_sizing_service requires aircraft geometry (cd0, e_oswald, AR, S); "
        "legacy estimate-only mode removed in gh-490. "
        "Use _combo_required_power_w with explicit geometry parameters."
    )


def _combo_required_power_w(
    speed_ms: float,
    total_mass_kg: float,
    altitude_m: float,
    cd0: float,
    e_oswald: float,
    ar: float,
    s_ref_m2: float,
    eta_total: float,
) -> float:
    """Power required for a specific motor+battery combo at cruise speed.

    Delegates physics to endurance_service._power_required with per-combo
    aerodynamic geometry rather than hardcoded constants (gh-490 Model A).
    """
    if speed_ms <= 0:
        return 0.0
    rho = _air_density(altitude_m)
    return _power_required(
        rho=rho,
        v=speed_ms,
        cd0=cd0,
        e=e_oswald,
        ar=ar,
        mass=total_mass_kg,
        s_ref=s_ref_m2,
        eta_total=eta_total,
    )


def _find_matching_esc(escs: list, min_current_a: float):
    """Return the first ESC that can handle the required current, or None."""
    for esc in escs:
        esc_specs = esc.specs or {}
        # gh-986 catalog stores continuous current under continuous_current_a;
        # fall back to legacy max_continuous_a for older entries (gh-992).
        cont_a = esc_specs.get("continuous_current_a", esc_specs.get("max_continuous_a", 0)) or 0
        if cont_a >= min_current_a:
            return esc
    return None


def _compute_confidence(flight_time_min: float, target_flight_time_min: float) -> float:
    """Confidence that a motor+battery combo meets the flight-time target.

    Smoothly scales with achieved/target ratio: meeting the target → 1.0,
    falling linearly toward 0 as flight time drops. No discontinuity
    (gh-992: the old /1.5 scaling capped an on-target combo at 0.667 and had a
    3.3x cliff at 50% of target)."""
    if target_flight_time_min <= 0:
        return 0.0
    return min(flight_time_min / target_flight_time_min, 1.0)


def _resolve_aero_params(
    request: PowertrainSizingRequest,
    context: dict[str, Any] | None,
) -> tuple[float, float, float, float, list[str]]:
    """Resolve aerodynamic parameters with a 3-tier priority (gh-960).

    Priority order per parameter:
      1. Explicit request field (user-supplied → most trusted)
      2. aeroplane.assumption_computation_context (computed from analysis, gh-924)
      3. RC-typical default → emits a warning note

    Returns
    -------
    (cd0, e_oswald, ar, s_ref_m2, warnings)
    """
    ctx = context or {}
    warnings: list[str] = []

    def _pick(
        request_val: float | None,
        ctx_key: str,
        default: float,
        label: str,
        param_name: str,
    ) -> float:
        if request_val is not None:
            return request_val
        ctx_val = ctx.get(ctx_key)
        if ctx_val is not None:
            return float(ctx_val)
        warnings.append(
            f"{label} not provided — assumed {default} (RC-typical). "
            f"Provide {param_name} in the request or run an aerodynamic analysis "
            f"to get an accurate power estimate."
        )
        return default

    cd0 = _pick(
        request.cd0,
        "cd0",
        _DEFAULT_CD0,
        "Zero-lift drag coefficient (cd0)",
        "cd0",
    )
    e_oswald = _pick(
        request.e_oswald,
        "e_oswald",
        _DEFAULT_E_OSWALD,
        "Oswald efficiency factor (e_oswald)",
        "e_oswald",
    )
    ar = _pick(
        request.aspect_ratio,
        "aspect_ratio",
        _DEFAULT_AR,
        "Wing aspect ratio (aspect_ratio)",
        "aspect_ratio",
    )
    s_ref_m2 = _pick(
        request.s_ref_m2,
        "s_ref_m2",
        _DEFAULT_S_REF_M2,
        "Wing reference area (s_ref_m2)",
        "s_ref_m2",
    )

    return cd0, e_oswald, ar, s_ref_m2, warnings


def _evaluate_motor_battery_combo(
    motor,
    battery,
    escs: list,
    request: PowertrainSizingRequest,
    cd0: float,
    e_oswald: float,
    ar: float,
    s_ref_m2: float,
) -> PowertrainCandidate | None:
    """Evaluate a single motor+battery combination; return a candidate or None.

    Aerodynamic geometry (cd0, e_oswald, ar, s_ref) are resolved once by the
    caller via _resolve_aero_params and passed in — no per-combo resolution.
    """
    motor_mass_kg = (motor.mass_g or 0) / 1000.0
    battery_mass_kg = (battery.mass_g or 0) / 1000.0
    battery_specs = battery.specs or {}
    capacity_mah = battery_specs.get("capacity_mah", 0)
    # The battery component_type schema stores nominal voltage as voltage_v
    # (gh-992); fall back to legacy keys, then derive from cell count (3.7 V/cell
    # nominal), then a 3S default — so a schema-valid battery isn't mis-read as 11.1 V.
    cells = battery_specs.get("cells")
    voltage = battery_specs.get("voltage_v")
    if voltage is None:
        voltage = battery_specs.get("voltage")
    if voltage is None:
        voltage = battery_specs.get("nominal_voltage")
    if voltage is None and cells:
        voltage = cells * 3.7
    if voltage is None:
        voltage = 11.1

    if capacity_mah <= 0 or voltage <= 0:
        return None

    total_mass = request.airframe_mass_kg + motor_mass_kg + battery_mass_kg

    eta_prop: float = request.eta_prop if request.eta_prop is not None else DEFAULT_ETA_PROP
    eta_motor: float = request.eta_motor if request.eta_motor is not None else DEFAULT_ETA_MOTOR
    eta_esc: float = request.eta_esc if request.eta_esc is not None else DEFAULT_ETA_ESC
    eta_total = eta_prop * eta_motor * eta_esc

    actual_cruise_power = _combo_required_power_w(
        speed_ms=request.target_cruise_speed_ms,
        total_mass_kg=total_mass,
        altitude_m=request.altitude_m,
        cd0=cd0,
        e_oswald=e_oswald,
        ar=ar,
        s_ref_m2=s_ref_m2,
        eta_total=eta_total,
    )

    cruise_current_a = actual_cruise_power / voltage if voltage > 0 else 999
    if request.max_current_draw_a and cruise_current_a > request.max_current_draw_a:
        return None

    capacity_ah = capacity_mah / 1000.0
    flight_time_h = (capacity_ah / cruise_current_a) * 0.8 if cruise_current_a > 0 else 0
    flight_time_min = flight_time_h * 60

    esc_match = _find_matching_esc(escs, cruise_current_a)

    return PowertrainCandidate(
        motor_id=motor.id,
        motor_name=motor.name,
        esc_id=esc_match.id if esc_match else None,
        esc_name=esc_match.name if esc_match else None,
        battery_id=battery.id,
        battery_name=battery.name,
        estimated_flight_time_min=round(flight_time_min, 1),
        estimated_cruise_power_w=round(actual_cruise_power, 1),
        estimated_top_speed_ms=round(request.target_top_speed_ms, 1),
        confidence=round(_compute_confidence(flight_time_min, request.target_flight_time_min), 3),
    )


def size_powertrain(
    db: Session, aeroplane_uuid, request: PowertrainSizingRequest
) -> PowertrainSizingResponse:
    aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_uuid).first()
    if not aeroplane:
        raise NotFoundError(entity="Aeroplane", resource_id=aeroplane_uuid)

    motors = (
        db.query(ComponentModel).filter(ComponentModel.component_type == "brushless_motor").all()
    )
    batteries = db.query(ComponentModel).filter(ComponentModel.component_type == "battery").all()
    escs = db.query(ComponentModel).filter(ComponentModel.component_type == "esc").all()

    if not motors or not batteries:
        # gh-992: never return a silent empty table — explain why so the UI can
        # tell the user what is missing instead of looking broken.
        empty_warnings: list[str] = []
        if not motors:
            empty_warnings.append(
                "No brushless motors in the component catalog — add motors "
                "(e.g. import the D-Power catalog) to size a powertrain."
            )
        if not batteries:
            empty_warnings.append(
                "No batteries in the component catalog — add LiPo batteries to "
                "compute flight time and current draw."
            )
        return PowertrainSizingResponse(recommendations=[], warnings=empty_warnings)

    # Resolve aero params once; collect warnings (gh-960)
    ctx = getattr(aeroplane, "assumption_computation_context", None) or {}
    cd0, e_oswald, ar, s_ref_m2, warnings = _resolve_aero_params(request, ctx)

    candidates: list[PowertrainCandidate] = []
    for motor in motors:
        for battery in batteries:
            candidate = _evaluate_motor_battery_combo(
                motor, battery, escs, request, cd0, e_oswald, ar, s_ref_m2
            )
            if candidate is not None:
                candidates.append(candidate)

    candidates.sort(key=lambda c: c.confidence, reverse=True)
    return PowertrainSizingResponse(recommendations=candidates[:10], warnings=warnings)
