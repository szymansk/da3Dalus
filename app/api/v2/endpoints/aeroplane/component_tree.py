"""Endpoints for the per-aeroplane component tree."""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.core.exceptions import (
    NotFoundError,
    ServiceException,
    ValidationDomainError,
    ValidationError,
)
from app.db.session import get_db
from app.schemas.component_tree import (
    ComponentTreeNodeRead,
    ComponentTreeNodeWrite,
    ComponentTreeResponse,
    MoveNodeRequest,
    WeightResponse,
)
from app.services import component_tree_service as svc

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/aeroplanes/{aeroplane_id}/component-tree",
    tags=["component-tree"],
)


def _raise_http(exc: ServiceException) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    if isinstance(exc, (ValidationError, ValidationDomainError)):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message) from exc


def _call(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except ServiceException as exc:
        _raise_http(exc)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    operation_id="get_component_tree",
)
async def get_component_tree(
    aeroplane_id: Annotated[str, Path(...)],
    db: Annotated[Session, Depends(get_db)],
) -> ComponentTreeResponse:
    """Get the full component tree for an aeroplane."""
    return _call(svc.get_tree, db, aeroplane_id)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    operation_id="add_tree_node",
)
async def add_tree_node(
    aeroplane_id: Annotated[str, Path(...)],
    body: Annotated[ComponentTreeNodeWrite, Body(...)],
    db: Annotated[Session, Depends(get_db)],
) -> ComponentTreeNodeRead:
    """Add a node to the component tree."""
    return _call(svc.add_node, db, aeroplane_id, body)


@router.put(
    "/{node_id}",
    status_code=status.HTTP_200_OK,
    operation_id="update_tree_node",
)
async def update_tree_node(
    aeroplane_id: Annotated[str, Path(...)],
    node_id: Annotated[int, Path(...)],
    body: Annotated[ComponentTreeNodeWrite, Body(...)],
    db: Annotated[Session, Depends(get_db)],
) -> ComponentTreeNodeRead:
    """Update a node in the component tree."""
    return _call(svc.update_node, db, aeroplane_id, node_id, body)


@router.delete(
    "/{node_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_tree_node",
)
async def delete_tree_node(
    aeroplane_id: Annotated[str, Path(...)],
    node_id: Annotated[int, Path(...)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a node from the tree. Synced nodes cannot be deleted (use move instead)."""
    _call(svc.delete_node, db, aeroplane_id, node_id)


@router.post(
    "/{node_id}/move",
    status_code=status.HTTP_200_OK,
    operation_id="move_tree_node",
)
async def move_tree_node(
    aeroplane_id: Annotated[str, Path(...)],
    node_id: Annotated[int, Path(...)],
    body: Annotated[MoveNodeRequest, Body(...)],
    db: Annotated[Session, Depends(get_db)],
) -> ComponentTreeNodeRead:
    """Move a node to a new parent position."""
    return _call(svc.move_node, db, aeroplane_id, node_id, body.new_parent_id, body.sort_index)


@router.get(
    "/{node_id}/weight",
    status_code=status.HTTP_200_OK,
    operation_id="get_node_weight",
)
async def get_node_weight(
    aeroplane_id: Annotated[str, Path(...)],
    node_id: Annotated[int, Path(...)],
    db: Annotated[Session, Depends(get_db)],
) -> WeightResponse:
    """Calculate the recursive weight for a node (own + all children)."""
    return _call(svc.calculate_weight, db, aeroplane_id, node_id)
