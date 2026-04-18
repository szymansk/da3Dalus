"""REST endpoints for Aeroplane-bound Construction Plans (gh#126)."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Body, Depends, Path
from fastapi import status
from sqlalchemy.orm import Session

from app.core.exceptions import ServiceException
from app.db.session import get_db
from app.schemas.construction_plan import (
    ExecuteRequest,
    ExecutionResult,
    InstantiateRequest,
    PlanRead,
    PlanSummary,
    ToTemplateRequest,
)
from app.services import construction_plan_service as svc

router = APIRouter()


def _handle_service_error(exc: ServiceException):
    from fastapi import HTTPException
    from app.core.exceptions import NotFoundError, ValidationError, InternalError

    status_map = {
        NotFoundError: status.HTTP_404_NOT_FOUND,
        ValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
        InternalError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    }
    code = status_map.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
    raise HTTPException(status_code=code, detail=str(exc.message))


@router.get(
    "/aeroplanes/{aeroplane_id}/construction-plans",
    response_model=List[PlanSummary],
    tags=["construction-plans"],
    operation_id="list_aeroplane_construction_plans",
)
async def list_aeroplane_plans(
    aeroplane_id: str = Path(...),
    db: Session = Depends(get_db),
) -> List[PlanSummary]:
    """List construction plans bound to an aeroplane."""
    try:
        return svc.list_plans(db, plan_type="plan", aeroplane_id=aeroplane_id)
    except ServiceException as exc:
        _handle_service_error(exc)


@router.post(
    "/aeroplanes/{aeroplane_id}/construction-plans/from-template/{template_id}",
    response_model=PlanRead,
    status_code=status.HTTP_201_CREATED,
    tags=["construction-plans"],
    operation_id="instantiate_construction_template",
)
async def instantiate_template(
    aeroplane_id: str = Path(...),
    template_id: int = Path(...),
    request: InstantiateRequest = Body(None),
    db: Session = Depends(get_db),
) -> PlanRead:
    """Create a concrete plan from a template, bound to an aeroplane."""
    try:
        return svc.instantiate_template(
            db,
            template_id,
            aeroplane_id,
            name=request.name if request else None,
        )
    except ServiceException as exc:
        _handle_service_error(exc)


@router.post(
    "/aeroplanes/{aeroplane_id}/construction-plans/{plan_id}/execute",
    response_model=ExecutionResult,
    tags=["construction-plans"],
    operation_id="execute_aeroplane_construction_plan",
)
async def execute_plan(
    aeroplane_id: str = Path(...),
    plan_id: int = Path(...),
    db: Session = Depends(get_db),
) -> ExecutionResult:
    """Execute a construction plan against an aeroplane configuration."""
    try:
        return svc.execute_plan(db, plan_id, ExecuteRequest(aeroplane_id=aeroplane_id))
    except ServiceException as exc:
        _handle_service_error(exc)


@router.post(
    "/aeroplanes/{aeroplane_id}/construction-plans/{plan_id}/to-template",
    response_model=PlanRead,
    status_code=status.HTTP_201_CREATED,
    tags=["construction-plans"],
    operation_id="plan_to_template",
)
async def plan_to_template(
    plan_id: int = Path(...),
    request: ToTemplateRequest = Body(None),
    db: Session = Depends(get_db),
) -> PlanRead:
    """Create a new template from an existing plan."""
    try:
        return svc.to_template(db, plan_id, name=request.name if request else None)
    except ServiceException as exc:
        _handle_service_error(exc)
