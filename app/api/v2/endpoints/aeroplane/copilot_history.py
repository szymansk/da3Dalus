import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Path, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ServiceException,
    ValidationDomainError,
    ValidationError,
)
from app.db.session import get_db
from app.schemas.copilot_history import CopilotHistory, CopilotMessageRead, CopilotMessageWrite
from app.services import copilot_history_service as svc

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


@router.get(
    "/aeroplanes/{aeroplane_id}/copilot-history",
    status_code=status.HTTP_200_OK,
    tags=["copilot-history"],
    operation_id="get_copilot_history",
    responses={
        404: {"description": "Resource not found"},
        409: {"description": "Conflict"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def get_copilot_history(
    aeroplane_id: Annotated[UUID4, Path(..., description="The ID of the aeroplane")],
    db: Annotated[Session, Depends(get_db)],
) -> CopilotHistory:
    """Get the full copilot chat history for the aeroplane."""
    return _call(svc.get_history, db, aeroplane_id)


@router.post(
    "/aeroplanes/{aeroplane_id}/copilot-history",
    status_code=status.HTTP_201_CREATED,
    tags=["copilot-history"],
    operation_id="append_copilot_message",
    responses={
        404: {"description": "Resource not found"},
        409: {"description": "Conflict"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def append_copilot_message(
    aeroplane_id: Annotated[UUID4, Path(..., description="The ID of the aeroplane")],
    body: Annotated[CopilotMessageWrite, Body(..., description="Message to append")],
    db: Annotated[Session, Depends(get_db)],
) -> CopilotMessageRead:
    """Append a new message to the copilot history."""
    return _call(svc.append_message, db, aeroplane_id, body)


@router.delete(
    "/aeroplanes/{aeroplane_id}/copilot-history",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["copilot-history"],
    operation_id="clear_copilot_history",
    responses={
        404: {"description": "Resource not found"},
        409: {"description": "Conflict"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def clear_copilot_history(
    aeroplane_id: Annotated[UUID4, Path(..., description="The ID of the aeroplane")],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Clear all copilot messages for the aeroplane."""
    _call(svc.clear_history, db, aeroplane_id)


@router.delete(
    "/aeroplanes/{aeroplane_id}/copilot-history/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["copilot-history"],
    operation_id="delete_copilot_message",
    responses={
        404: {"description": "Resource not found"},
        409: {"description": "Conflict"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def delete_copilot_message(
    aeroplane_id: Annotated[UUID4, Path(..., description="The ID of the aeroplane")],
    message_id: Annotated[int, Path(..., description="The ID of the message to delete")],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a single copilot message."""
    _call(svc.delete_message, db, aeroplane_id, message_id)
