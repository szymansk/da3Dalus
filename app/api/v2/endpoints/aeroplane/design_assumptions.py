"""Design Assumptions endpoints — CRUD for per-aeroplane design parameters."""

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
from app.schemas.design_assumption import (
    AssumptionRead,
    AssumptionSourceSwitch,
    AssumptionWrite,
    AssumptionsSummary,
)
from app.services import design_assumptions_service as svc

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
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


_PARAM_NAME_PATTERN = r"^(mass|cg_x|target_static_margin|cd0|cl_max|g_limit)$"


@router.post(
    "/aeroplanes/{aeroplane_id}/assumptions",
    status_code=status.HTTP_201_CREATED,
    tags=["design-assumptions"],
    operation_id="seed_assumptions",
    responses={
        404: {"description": "Resource not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def seed_assumptions_endpoint(
    aeroplane_id: Annotated[UUID4, Path(..., description="The ID of the aeroplane")],
    db: Annotated[Session, Depends(get_db)],
) -> AssumptionsSummary:
    """Seed default design assumptions for an aeroplane (idempotent)."""
    return _call(svc.seed_defaults, db, aeroplane_id)


@router.get(
    "/aeroplanes/{aeroplane_id}/assumptions",
    status_code=status.HTTP_200_OK,
    tags=["design-assumptions"],
    operation_id="list_assumptions",
    responses={
        404: {"description": "Resource not found"},
        500: {"description": "Internal server error"},
    },
)
async def list_assumptions_endpoint(
    aeroplane_id: Annotated[UUID4, Path(..., description="The ID of the aeroplane")],
    db: Annotated[Session, Depends(get_db)],
) -> AssumptionsSummary:
    """List all design assumptions with divergence info."""
    return _call(svc.list_assumptions, db, aeroplane_id)


@router.put(
    "/aeroplanes/{aeroplane_id}/assumptions/{param_name}",
    status_code=status.HTTP_200_OK,
    tags=["design-assumptions"],
    operation_id="update_assumption",
    responses={
        404: {"description": "Resource not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def update_assumption_endpoint(
    aeroplane_id: Annotated[UUID4, Path(..., description="The ID of the aeroplane")],
    param_name: Annotated[
        str, Path(..., description="Parameter name", pattern=_PARAM_NAME_PATTERN)
    ],
    body: Annotated[AssumptionWrite, Body(..., description="New estimate value")],
    db: Annotated[Session, Depends(get_db)],
) -> AssumptionRead:
    """Update the estimate value of a design assumption parameter."""
    return _call(svc.update_assumption, db, aeroplane_id, param_name, body)


@router.patch(
    "/aeroplanes/{aeroplane_id}/assumptions/{param_name}/source",
    status_code=status.HTTP_200_OK,
    tags=["design-assumptions"],
    operation_id="switch_assumption_source",
    responses={
        404: {"description": "Resource not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def switch_source_endpoint(
    aeroplane_id: Annotated[UUID4, Path(..., description="The ID of the aeroplane")],
    param_name: Annotated[
        str, Path(..., description="Parameter name", pattern=_PARAM_NAME_PATTERN)
    ],
    body: Annotated[AssumptionSourceSwitch, Body(..., description="Source to switch to")],
    db: Annotated[Session, Depends(get_db)],
) -> AssumptionRead:
    """Switch a design assumption between ESTIMATE and CALCULATED sources."""
    return _call(svc.switch_source, db, aeroplane_id, param_name, body)
