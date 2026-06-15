"""Powertrain Sizing Modal Service (gh-197).

Returns the pre-filled defaults for the Powertrain Sizing Modal dialog:
  - cd0 / s_ref_m2 from the aeroplane's assumption_computation_context (gh-924)
  - motors from the brushless_motor component catalog with efficiency_pct
  - warnings when values are defaulted (same pattern as gh-960)

The caller (endpoint) resolves the aeroplane by UUID and passes it in.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.aeroplanemodel import AeroplaneModel
from app.models.component import ComponentModel
from app.schemas.powertrain_sizing_modal import (
    MotorSuggestion,
    PowertrainModalParamsResponse,
)

logger = logging.getLogger(__name__)

# Brushless motor defaults — typical high-quality RC/UAV motor.
DEFAULT_MOTOR_ETA: float = 0.85  # 85 % shaft efficiency (editable in modal)
DEFAULT_ETA_PROP: float = 0.65  # Placeholder; prop-finder is Phase 2 (#199)

# RC-typical aero fallbacks (mirrors powertrain_sizing_service)
_DEFAULT_CD0: float = 0.03
_DEFAULT_S_REF_M2: float = 0.5


def _resolve_cd0(ctx: dict[str, Any]) -> tuple[float, str | None]:
    """Return (cd0, warning_or_None) from the gh-924 computation context."""
    val = ctx.get("cd0")
    if val is not None and float(val) > 0:
        return float(val), None
    return _DEFAULT_CD0, (
        "cd0 not available in aerodynamic analysis context — using RC-typical default "
        f"({_DEFAULT_CD0}). Run recompute to get an accurate value."
    )


def _resolve_s_ref(ctx: dict[str, Any]) -> tuple[float, str | None]:
    """Return (s_ref_m2, warning_or_None) from the gh-924 computation context."""
    val = ctx.get("s_ref_m2")
    if val is not None and float(val) > 0:
        return float(val), None
    return _DEFAULT_S_REF_M2, (
        "s_ref_m2 not available in aerodynamic analysis context — using RC-typical "
        f"default ({_DEFAULT_S_REF_M2} m²). Run recompute to get the real wing area."
    )


def _motor_to_suggestion(m: ComponentModel) -> MotorSuggestion:
    """Convert a ComponentModel (brushless_motor) to a MotorSuggestion.

    efficiency_pct comes from specs['efficiency_pct'] when present; otherwise
    the brushless-motor default (DEFAULT_MOTOR_ETA × 100) is used so the
    dialog always has a sensible starting value.
    """
    specs: dict[str, Any] = m.specs or {}
    raw_eff = specs.get("efficiency_pct")
    efficiency_pct = float(raw_eff) if raw_eff is not None else DEFAULT_MOTOR_ETA * 100.0

    # D-Drive motors store gear_ratio in specs (gh-986); the KV shown in the
    # modal is the raw motor KV from specs (before any gearing) — the designer
    # is picking the motor, not the propulsion output shaft.
    raw_kv = specs.get("kv")
    kv = float(raw_kv) if raw_kv is not None else None

    raw_power = specs.get("max_power_w") or specs.get("max_continuous_power_w")
    max_power_w = float(raw_power) if raw_power is not None else None

    return MotorSuggestion(
        id=m.id,
        name=m.name,
        manufacturer=m.manufacturer,
        mass_g=m.mass_g,
        efficiency_pct=efficiency_pct,
        kv=kv,
        max_power_w=max_power_w,
        description=m.description,
    )


def get_modal_params(db: Session, aeroplane_uuid) -> PowertrainModalParamsResponse:
    """Return pre-filled defaults for the Powertrain Sizing Modal.

    Raises
    ------
    NotFoundError
        When the aeroplane UUID does not exist in the database.
    """
    aeroplane: AeroplaneModel | None = (
        db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_uuid).first()
    )
    if aeroplane is None:
        raise NotFoundError(entity="Aeroplane", resource_id=aeroplane_uuid)

    ctx: dict[str, Any] = getattr(aeroplane, "assumption_computation_context", None) or {}

    cd0, cd0_warn = _resolve_cd0(ctx)
    s_ref_m2, sref_warn = _resolve_s_ref(ctx)

    warnings: list[str] = [w for w in [cd0_warn, sref_warn] if w is not None]

    # Default motor efficiency: prefer the motor-level default; the user overrides
    # this in the modal when they select a specific motor (its efficiency_pct from
    # specs is pre-populated by the motor list).
    eta_motor = DEFAULT_MOTOR_ETA

    # Motor catalog
    motors_raw: list[ComponentModel] = (
        db.query(ComponentModel).filter(ComponentModel.component_type == "brushless_motor").all()
    )
    motors = sorted(
        [_motor_to_suggestion(m) for m in motors_raw],
        key=lambda m: m.name,
    )

    return PowertrainModalParamsResponse(
        altitude_m=0.0,  # no altitude field in current mission model; default sea-level
        cd0=cd0,
        s_ref_m2=s_ref_m2,
        eta_prop=DEFAULT_ETA_PROP,
        eta_motor=eta_motor,
        motors=motors,
        warnings=warnings,
    )
