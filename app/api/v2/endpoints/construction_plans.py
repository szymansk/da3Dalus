"""REST endpoints for Construction Plans (gh#101)."""
from __future__ import annotations

import logging
from typing import Annotated, List

from fastapi import APIRouter, Body, Depends, Path, Query
from fastapi import status
from sqlalchemy.orm import Session

from app.core.exceptions import (
    NotFoundError,
    ValidationError,
    InternalError,
    ServiceException,
)
from app.db.session import get_db
from app.schemas.construction_plan import (
    ArtifactDirectory,
    ArtifactFile,
    CreatorInfo,
    ExecuteRequest,
    ExecutionResult,
    PlanCreate,
    PlanRead,
    PlanSummary,
)
from app.services import artifact_service
from app.services import construction_plan_service as svc

logger = logging.getLogger(__name__)

router = APIRouter()


def _handle_service_error(exc: ServiceException):
    """Convert domain exceptions to HTTP responses."""
    from fastapi import HTTPException

    status_map = {
        NotFoundError: status.HTTP_404_NOT_FOUND,
        ValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
        InternalError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    }
    code = status_map.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
    raise HTTPException(status_code=code, detail=str(exc.message))


# ── Creator catalog (MUST be before /{plan_id} to avoid route conflict) ──


@router.get(
    "/construction-plans/creators",
    status_code=status.HTTP_200_OK,
    tags=["construction-plans"],
    operation_id="list_creators"
)
async def list_creators() -> List[CreatorInfo]:
    """List all available Creator classes with their parameters."""
    return svc.list_creators()


# ── CRUD ────────────────────────────────────────────────────────


@router.get(
    "/construction-plans",
    status_code=status.HTTP_200_OK,
    tags=["construction-plans"],
    operation_id="list_construction_plans"
)
async def list_plans(
    db: Annotated[Session, Depends(get_db)],
    plan_type: Annotated[str | None, Query(description="Filter by plan type")] = None,
) -> List[PlanSummary]:
    """List all construction plans, optionally filtered by plan_type."""
    try:
        return svc.list_plans(db, plan_type=plan_type)
    except ServiceException as exc:
        _handle_service_error(exc)


@router.post(
    "/construction-plans",
    status_code=status.HTTP_201_CREATED,
    tags=["construction-plans"],
    operation_id="create_construction_plan"
)
async def create_plan(
    request: Annotated[PlanCreate, Body(...)],
    db: Annotated[Session, Depends(get_db)],
) -> PlanRead:
    """Create a new construction plan."""
    try:
        return svc.create_plan(db, request)
    except ServiceException as exc:
        _handle_service_error(exc)


@router.get(
    "/construction-plans/{plan_id}",
    status_code=status.HTTP_200_OK,
    tags=["construction-plans"],
    operation_id="get_construction_plan"
)
async def get_plan(
    plan_id: Annotated[int, Path(..., description="Construction plan ID")],
    db: Annotated[Session, Depends(get_db)],
) -> PlanRead:
    """Get a construction plan by ID."""
    try:
        return svc.get_plan(db, plan_id)
    except ServiceException as exc:
        _handle_service_error(exc)


@router.put(
    "/construction-plans/{plan_id}",
    status_code=status.HTTP_200_OK,
    tags=["construction-plans"],
    operation_id="update_construction_plan"
)
async def update_plan(
    plan_id: Annotated[int, Path(...)],
    request: Annotated[PlanCreate, Body(...)],
    db: Annotated[Session, Depends(get_db)],
) -> PlanRead:
    """Update an existing construction plan."""
    try:
        return svc.update_plan(db, plan_id, request)
    except ServiceException as exc:
        _handle_service_error(exc)


@router.delete(
    "/construction-plans/{plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["construction-plans"],
    operation_id="delete_construction_plan",
)
async def delete_plan(
    plan_id: Annotated[int, Path(...)],
    db: Annotated[Session, Depends(get_db)],
):
    """Delete a construction plan."""
    try:
        svc.delete_plan(db, plan_id)
    except ServiceException as exc:
        _handle_service_error(exc)


# ── Execute ─────────────────────────────────────────────────────


@router.post(
    "/construction-plans/{plan_id}/execute",
    status_code=status.HTTP_200_OK,
    tags=["construction-plans"],
    operation_id="execute_construction_plan"
)
async def execute_plan(
    plan_id: Annotated[int, Path(...)],
    request: Annotated[ExecuteRequest, Body(...)],
    db: Annotated[Session, Depends(get_db)],
) -> ExecutionResult:
    """Execute a construction plan against an aeroplane configuration."""
    try:
        return svc.execute_plan(db, plan_id, request)
    except ServiceException as exc:
        _handle_service_error(exc)


# ── Artifact browser ───────────────────────────────────────────


@router.get(
    "/construction-plans/{plan_id}/artifacts",
    tags=["construction-plans"],
    operation_id="list_plan_artifacts",
)
async def list_artifacts(
    plan_id: Annotated[int, Path(...)],
) -> List[ArtifactDirectory]:
    """List all execution artifact directories for a plan."""
    try:
        return artifact_service.list_executions(plan_id)
    except ServiceException as exc:
        _handle_service_error(exc)


@router.get(
    "/construction-plans/{plan_id}/artifacts/{execution_id}",
    tags=["construction-plans"],
    operation_id="list_artifact_files",
)
async def list_artifact_files(
    plan_id: Annotated[int, Path(...)],
    execution_id: Annotated[str, Path(...)],
) -> List[ArtifactFile]:
    """List files in a specific execution's artifact directory."""
    try:
        return artifact_service.list_files(plan_id, execution_id)
    except ServiceException as exc:
        _handle_service_error(exc)


@router.get(
    "/construction-plans/{plan_id}/artifacts/{execution_id}/{filename}",
    tags=["construction-plans"],
    operation_id="download_artifact_file",
)
async def download_artifact_file(
    plan_id: Annotated[int, Path(...)],
    execution_id: Annotated[str, Path(...)],
    filename: Annotated[str, Path(...)],
):
    """Download a single artifact file."""
    from fastapi.responses import FileResponse

    try:
        path = artifact_service.get_file_path(plan_id, execution_id, filename)
        return FileResponse(path, filename=filename)
    except ServiceException as exc:
        _handle_service_error(exc)


@router.delete(
    "/construction-plans/{plan_id}/artifacts/{execution_id}/{filename}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["construction-plans"],
    operation_id="delete_artifact_file",
)
async def delete_artifact_file(
    plan_id: Annotated[int, Path(...)],
    execution_id: Annotated[str, Path(...)],
    filename: Annotated[str, Path(...)],
):
    """Delete a single artifact file."""
    try:
        artifact_service.delete_file(plan_id, execution_id, filename)
    except ServiceException as exc:
        _handle_service_error(exc)
