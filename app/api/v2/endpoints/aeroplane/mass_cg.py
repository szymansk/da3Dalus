"""Mass / CG design parameter endpoints."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Path, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    InternalError,
    NotFoundError,
    ServiceException,
    ValidationDomainError,
    ValidationError,
)
from app.db.session import get_db
from app.schemas.mass_cg import (
    CGComparisonResponse,
    DesignMetricsRequest,
    DesignMetricsResponse,
    MassSweepRequest,
    MassSweepResponse,
)
from app.services import mass_cg_service as svc

logger = logging.getLogger(__name__)

router = APIRouter()


def _raise_http(exc: ServiceException) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    if isinstance(exc, (ValidationError, ValidationDomainError)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message
        ) from exc
    if isinstance(exc, ConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message
    ) from exc


def _call(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except ServiceException as exc:
        _raise_http(exc)
    except Exception as exc:
        logger.error("Unexpected error in mass_cg: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.post(
    "/aeroplanes/{aeroplane_id}/design_metrics",
    status_code=status.HTTP_200_OK,
    tags=["mass-cg"],
    operation_id="compute_design_metrics",
    responses={
        404: {"description": "Resource not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def design_metrics_endpoint(
    aeroplane_id: Annotated[UUID4, Path(..., description="The ID of the aeroplane")],
    body: Annotated[DesignMetricsRequest, Body(..., description="Flight condition")],
    db: Annotated[Session, Depends(get_db)],
) -> DesignMetricsResponse:
    """Compute mass-dependent design metrics (stall speed, wing loading, required CL)."""
    return _call(
        svc.get_design_metrics_for_aeroplane,
        db,
        aeroplane_id,
        body.velocity,
        body.altitude,
    )


@router.post(
    "/aeroplanes/{aeroplane_id}/mass_sweep",
    status_code=status.HTTP_200_OK,
    tags=["mass-cg"],
    operation_id="compute_mass_sweep",
    responses={
        404: {"description": "Resource not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def mass_sweep_endpoint(
    aeroplane_id: Annotated[UUID4, Path(..., description="The ID of the aeroplane")],
    body: Annotated[MassSweepRequest, Body(..., description="Sweep parameters")],
    db: Annotated[Session, Depends(get_db)],
) -> MassSweepResponse:
    """Sweep mass values and compute derived metrics at each point (no aero re-run)."""
    return _call(
        svc.get_mass_sweep_for_aeroplane,
        db,
        aeroplane_id,
        body.masses_kg,
        body.velocity,
        body.altitude,
    )


@router.get(
    "/aeroplanes/{aeroplane_id}/cg_comparison",
    status_code=status.HTTP_200_OK,
    tags=["mass-cg"],
    operation_id="get_cg_comparison",
    responses={
        404: {"description": "Resource not found"},
        500: {"description": "Internal server error"},
    },
)
async def cg_comparison_endpoint(
    aeroplane_id: Annotated[UUID4, Path(..., description="The ID of the aeroplane")],
    db: Annotated[Session, Depends(get_db)],
) -> CGComparisonResponse:
    """Compare design CG (from assumptions) with component-tree CG (from weight items)."""
    return _call(svc.get_cg_comparison, db, aeroplane_id)
