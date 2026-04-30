from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from app.core.exceptions import ServiceException
from app.db.session import get_db
from app.schemas.avl_geometry import AvlGeometryResponse, AvlGeometryUpdateRequest
from app.services import avl_geometry_service

from .base import _raise_http_from_domain

router = APIRouter()


@router.get(
    "/aeroplanes/{aeroplane_id}/avl-geometry",
    status_code=status.HTTP_200_OK,
    tags=["avl-geometry"],
    operation_id="get_avl_geometry",
)
async def get_avl_geometry(
    aeroplane_id: UUID4,
    db: Annotated[Session, Depends(get_db)],
) -> AvlGeometryResponse:
    try:
        return avl_geometry_service.get_avl_geometry(db, aeroplane_id)
    except ServiceException as exc:
        _raise_http_from_domain(exc)


@router.put(
    "/aeroplanes/{aeroplane_id}/avl-geometry",
    status_code=status.HTTP_200_OK,
    tags=["avl-geometry"],
    operation_id="save_avl_geometry",
)
async def save_avl_geometry(
    aeroplane_id: UUID4,
    body: AvlGeometryUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
) -> AvlGeometryResponse:
    try:
        return avl_geometry_service.save_avl_geometry(db, aeroplane_id, body.content)
    except ServiceException as exc:
        _raise_http_from_domain(exc)


@router.post(
    "/aeroplanes/{aeroplane_id}/avl-geometry/regenerate",
    status_code=status.HTTP_200_OK,
    tags=["avl-geometry"],
    operation_id="regenerate_avl_geometry",
)
async def regenerate_avl_geometry(
    aeroplane_id: UUID4,
    db: Annotated[Session, Depends(get_db)],
) -> AvlGeometryResponse:
    try:
        return avl_geometry_service.regenerate_avl_geometry(db, aeroplane_id)
    except ServiceException as exc:
        _raise_http_from_domain(exc)


@router.delete(
    "/aeroplanes/{aeroplane_id}/avl-geometry",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["avl-geometry"],
    operation_id="delete_avl_geometry",
)
async def delete_avl_geometry(
    aeroplane_id: UUID4,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    try:
        avl_geometry_service.delete_avl_geometry(db, aeroplane_id)
    except ServiceException as exc:
        _raise_http_from_domain(exc)
