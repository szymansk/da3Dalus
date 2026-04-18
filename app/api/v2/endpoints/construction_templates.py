"""REST endpoints for Construction Templates (gh#126)."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Body, Depends
from fastapi import status
from sqlalchemy.orm import Session

from app.core.exceptions import ServiceException
from app.db.session import get_db
from app.schemas.construction_plan import (
    PlanCreate,
    PlanRead,
    PlanSummary,
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
    "/construction-templates",
    response_model=List[PlanSummary],
    tags=["construction-templates"],
    operation_id="list_construction_templates",
)
async def list_templates(db: Session = Depends(get_db)) -> List[PlanSummary]:
    """List all construction templates."""
    try:
        return svc.list_plans(db, plan_type="template")
    except ServiceException as exc:
        _handle_service_error(exc)


@router.post(
    "/construction-templates",
    response_model=PlanRead,
    status_code=status.HTTP_201_CREATED,
    tags=["construction-templates"],
    operation_id="create_construction_template",
)
async def create_template(
    request: PlanCreate = Body(...),
    db: Session = Depends(get_db),
) -> PlanRead:
    """Create a new construction template."""
    request.plan_type = "template"
    request.aeroplane_id = None
    try:
        return svc.create_plan(db, request)
    except ServiceException as exc:
        _handle_service_error(exc)
