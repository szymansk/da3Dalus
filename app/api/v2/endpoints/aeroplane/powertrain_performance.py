"""Powertrain Performance endpoint (gh-615).

POST /aeroplanes/{aeroplane_id}/powertrain/performance

Accepts structured component references (motor, battery, propeller polar IDs)
and returns T(V), P(V), η_prop(J) curves.

The endpoint resolves each component from the DB, extracts its specs, fetches
the propeller polar samples, and delegates to
app.services.powertrain_performance.compute_performance_curve.
"""

from __future__ import annotations

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Path, status
from pydantic import UUID4, BaseModel, Field
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ServiceException, ValidationError
from app.db.session import get_db
from app.models.aeroplanemodel import AeroplaneModel
from app.models.component import ComponentModel
from app.models.prop_polar import PropellerPolarModel, PropellerPolarSampleModel
from app.services.powertrain_performance import (
    BatterySpec,
    MotorSpec,
    PowertrainPerformanceRequest,
    PowertrainPerformanceResponse,
    PropellerPolarRow,
    compute_performance_curve,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request schema for the endpoint
# ---------------------------------------------------------------------------


class PowertrainPerformanceEndpointRequest(BaseModel):
    """Identifies the powertrain components and propeller to evaluate."""

    motor_component_id: int = Field(..., description="Component catalog ID of the brushless_motor")
    battery_component_id: int = Field(..., description="Component catalog ID of the battery")
    propeller_polar_id: int = Field(..., description="ID from propeller_polars table (gh-995)")
    v_min_ms: float = Field(0.0, ge=0.0, description="Start of velocity range [m/s]")
    v_max_ms: float = Field(30.0, gt=0.0, description="End of velocity range [m/s]")
    n_points: int = Field(20, ge=1, le=200, description="Number of velocity samples")
    altitude_m: float = Field(0.0, ge=0.0, description="Operating altitude [m]")
    throttle: float = Field(1.0, gt=0.0, le=1.0, description="Throttle fraction")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _raise_http(exc: ServiceException) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    if isinstance(exc, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message
    ) from exc


def _resolve_motor(motor_row: ComponentModel) -> MotorSpec:
    """Extract MotorSpec from a brushless_motor ComponentModel."""
    specs = motor_row.specs or {}
    raw_kv = specs.get("kv_rpm_per_volt") or specs.get("kv")
    if not raw_kv:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Component {motor_row.id} ({motor_row.name!r}) has no kv_rpm_per_volt in specs.",
        )

    cells_max = specs.get("cells_lipo_max")
    if not cells_max:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Component {motor_row.id} ({motor_row.name!r}) has no cells_lipo_max in specs.",
        )

    return MotorSpec(
        kv_rpm_per_volt=float(raw_kv),
        gear_ratio=specs.get("gear_ratio"),
        efficiency_pct=specs.get("efficiency_pct"),
        cells_lipo_max=int(cells_max),
        io_no_load_a=specs.get("io_no_load_a"),
        max_current_a=specs.get("max_current_a"),
        continuous_current_a=specs.get("continuous_current_a"),
        # gh-1006: enables the QPROP 3-param torque-balance model when present
        rm_ohm=specs.get("rm_ohm"),
    )


def _resolve_battery(battery_row: ComponentModel) -> BatterySpec:
    """Extract BatterySpec from a battery ComponentModel."""
    specs = battery_row.specs or {}
    cells = specs.get("cells")
    capacity_mah = specs.get("capacity_mah")

    if not cells or not capacity_mah:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Battery component {battery_row.id} ({battery_row.name!r}) "
                "must have 'cells' and 'capacity_mah' in specs."
            ),
        )

    return BatterySpec(
        cells=int(cells),
        capacity_mah=float(capacity_mah),
        c_rate=specs.get("c_rate"),
    )


def _load_polar_rows(
    db: Session, polar_id: int
) -> tuple[PropellerPolarModel, list[PropellerPolarRow]]:
    """Load PropellerPolarModel + all its samples from DB."""
    polar = db.get(PropellerPolarModel, polar_id)
    if polar is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Propeller polar {polar_id} not found.",
        )

    sample_rows = (
        db.query(PropellerPolarSampleModel)
        .filter(PropellerPolarSampleModel.propeller_id == polar_id)
        .all()
    )

    if not sample_rows:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Propeller polar {polar_id} has no sample rows.",
        )

    rows = [
        PropellerPolarRow(
            rpm=s.rpm,
            J=s.J,
            Ct=s.Ct,
            Cp=s.Cp,
            Pe=s.Pe,
            PWR_W=s.PWR_W,
            Torque_Nm=s.Torque_Nm,
            Thrust_N=s.Thrust_N,
        )
        for s in sample_rows
    ]
    return polar, rows


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/aeroplanes/{aeroplane_id}/powertrain/performance",
    status_code=status.HTTP_200_OK,
    tags=["powertrain"],
    operation_id="compute_powertrain_performance",
    summary=(
        "Compute T(V)/P(V)/η(J) performance curves for a motor+propeller+battery "
        "combination (gh-615)"
    ),
    responses={
        404: {"description": "Aeroplane, motor, battery, or propeller polar not found"},
        422: {"description": "Validation error or missing component specs"},
        500: {"description": "Internal server error"},
    },
)
async def compute_powertrain_performance(
    aeroplane_id: Annotated[UUID4, Path(..., description="The UUID of the aeroplane")],
    body: Annotated[
        PowertrainPerformanceEndpointRequest,
        Body(..., description="Component IDs and velocity range"),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> PowertrainPerformanceResponse:
    """Return T(V), P_shaft(V), η_prop(J) curves for a powertrain combination.

    Resolves motor + battery from the component catalog and propeller polars
    from propeller_polars/propeller_polar_samples, then delegates to the
    powertrain performance service.

    The aeroplane must exist (ensures the request is anchored to a valid design
    context), but no aeroplane-level data is read for the computation itself.
    """
    # Verify aeroplane exists
    aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
    if aeroplane is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aeroplane {aeroplane_id} not found.",
        )

    # Resolve motor
    motor_row = db.get(ComponentModel, body.motor_component_id)
    if motor_row is None or motor_row.component_type != "brushless_motor":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brushless motor component {body.motor_component_id} not found.",
        )

    # Resolve battery
    battery_row = db.get(ComponentModel, body.battery_component_id)
    if battery_row is None or battery_row.component_type != "battery":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Battery component {body.battery_component_id} not found.",
        )

    motor_spec = _resolve_motor(motor_row)
    battery_spec = _resolve_battery(battery_row)
    polar_header, polar_rows = _load_polar_rows(db, body.propeller_polar_id)

    diameter_in = polar_header.diameter_in
    if not diameter_in or diameter_in <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Propeller polar {body.propeller_polar_id} has no valid diameter_in. "
                "Re-import the propeller data to fix missing geometry."
            ),
        )

    perf_request = PowertrainPerformanceRequest(
        motor=motor_spec,
        battery=battery_spec,
        propeller_diameter_in=diameter_in,
        polar_samples=polar_rows,
        v_min_ms=body.v_min_ms,
        v_max_ms=body.v_max_ms,
        n_points=body.n_points,
        altitude_m=body.altitude_m,
        throttle=body.throttle,
    )

    try:
        result = compute_performance_curve(perf_request)
    except Exception as exc:
        logger.exception("Powertrain performance computation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Performance computation failed: {exc}",
        ) from exc

    return result
