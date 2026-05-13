"""Loading Scenario endpoints (gh-488) — CG envelope from loading scenarios."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
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
from app.schemas.loading_scenario import (
    CgEnvelopeRead,
    LoadingScenarioCreate,
    LoadingScenarioRead,
    LoadingScenarioUpdate,
)
from app.services import loading_scenario_service as svc
from app.services.loading_template_service import get_templates_for_class

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


@router.get(
    "/aeroplanes/{aeroplane_id}/loading-scenarios",
    status_code=status.HTTP_200_OK,
    tags=["loading-scenarios"],
    operation_id="list_loading_scenarios",
    response_model=list[LoadingScenarioRead],
    responses={
        404: {"description": "Aeroplane not found"},
        500: {"description": "Internal server error"},
    },
)
async def list_loading_scenarios(
    aeroplane_id: Annotated[UUID4, Path(description="Aeroplane UUID")],
    db: Annotated[Session, Depends(get_db)],
) -> list[LoadingScenarioRead]:
    """List all loading scenarios for an aeroplane."""
    return _call(svc.list_scenarios, db, aeroplane_id)


@router.post(
    "/aeroplanes/{aeroplane_id}/loading-scenarios",
    status_code=status.HTTP_201_CREATED,
    tags=["loading-scenarios"],
    operation_id="create_loading_scenario",
    response_model=LoadingScenarioRead,
    responses={
        404: {"description": "Aeroplane not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def create_loading_scenario(
    aeroplane_id: Annotated[UUID4, Path(description="Aeroplane UUID")],
    body: Annotated[LoadingScenarioCreate, Body(description="Loading scenario to create")],
    db: Annotated[Session, Depends(get_db)],
) -> LoadingScenarioRead:
    """Create a new loading scenario for an aeroplane.

    A loading scenario defines a named CG loadout via component overrides
    and adhoc items (pilot, payload, ballast, etc.).  The union of all
    scenarios produces the Loading-Envelope.

    Creating a scenario marks all operating points as DIRTY and triggers a
    retrim at the envelope extremes.
    """
    return _call(svc.create_scenario, db, aeroplane_id, body)


@router.patch(
    "/aeroplanes/{aeroplane_id}/loading-scenarios/{scenario_id}",
    status_code=status.HTTP_200_OK,
    tags=["loading-scenarios"],
    operation_id="update_loading_scenario",
    response_model=LoadingScenarioRead,
    responses={
        404: {"description": "Aeroplane or scenario not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def update_loading_scenario(
    aeroplane_id: Annotated[UUID4, Path(description="Aeroplane UUID")],
    scenario_id: Annotated[int, Path(description="Scenario ID")],
    body: Annotated[LoadingScenarioUpdate, Body(description="Fields to update")],
    db: Annotated[Session, Depends(get_db)],
) -> LoadingScenarioRead:
    """Partially update a loading scenario."""
    return _call(svc.update_scenario, db, aeroplane_id, scenario_id, body)


@router.delete(
    "/aeroplanes/{aeroplane_id}/loading-scenarios/{scenario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["loading-scenarios"],
    operation_id="delete_loading_scenario",
    responses={
        404: {"description": "Aeroplane or scenario not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_loading_scenario(
    aeroplane_id: Annotated[UUID4, Path(description="Aeroplane UUID")],
    scenario_id: Annotated[int, Path(description="Scenario ID")],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a loading scenario."""
    _call(svc.delete_scenario, db, aeroplane_id, scenario_id)


@router.get(
    "/aeroplanes/{aeroplane_id}/cg-envelope",
    status_code=status.HTTP_200_OK,
    tags=["loading-scenarios"],
    operation_id="get_cg_envelope",
    response_model=CgEnvelopeRead,
    responses={
        404: {"description": "Aeroplane not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_cg_envelope(
    aeroplane_id: Annotated[UUID4, Path(description="Aeroplane UUID")],
    db: Annotated[Session, Depends(get_db)],
) -> CgEnvelopeRead:
    """Get the CG envelope for an aeroplane.

    Returns both the Loading-Envelope (min/max CG from all loading scenarios)
    and the Stability-Envelope (physically permissible CG range from aerodynamics),
    plus a classification and validation warnings.

    Classification (relative to target_static_margin — Scholz §4.2):
      error: SM < 0.02 or SM > 0.30
      warn:  0.02 ≤ SM < target or 0.20 < SM ≤ 0.30
      ok:    target ≤ SM ≤ 0.20
    """
    return _call(svc.get_cg_envelope, db, aeroplane_id)


@router.get(
    "/aeroplanes/{aeroplane_id}/loading-scenarios/templates",
    status_code=status.HTTP_200_OK,
    tags=["loading-scenarios"],
    operation_id="get_loading_scenario_templates",
    responses={
        404: {"description": "Aeroplane not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_loading_scenario_templates(
    aeroplane_id: Annotated[UUID4, Path(description="Aeroplane UUID")],
    db: Annotated[Session, Depends(get_db)],
    aircraft_class: Annotated[
        str,
        Query(description="Aircraft class: rc_trainer | rc_aerobatic | rc_combust | uav_survey | glider | boxwing"),
    ] = "rc_trainer",
) -> list[dict]:
    """Get default loading scenario templates for the given aircraft class.

    Templates provide a sensible starting set of scenarios (Battery Fwd/Aft,
    With/Without Payload, etc.) that the user can customise or discard.
    They are NOT automatically created at aeroplane creation.
    """
    # Verify the aeroplane exists
    _call(svc.list_scenarios, db, aeroplane_id)
    return get_templates_for_class(aircraft_class)
