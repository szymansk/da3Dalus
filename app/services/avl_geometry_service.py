"""Service layer for AVL geometry file CRUD and on-the-fly generation (gh-381)."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import InternalError, NotFoundError
from app.models.avl_geometry_file import AvlGeometryFileModel
from app.models.aeroplanemodel import AeroplaneModel
from app.schemas.avl_geometry import AvlGeometryResponse

logger = logging.getLogger(__name__)


def _get_aeroplane_or_raise(db: Session, aeroplane_uuid) -> AeroplaneModel:
    try:
        aeroplane = (
            db.query(AeroplaneModel)
            .filter(AeroplaneModel.uuid == aeroplane_uuid)
            .first()
        )
    except SQLAlchemyError as e:
        logger.error("Database error looking up aeroplane: %s", e)
        raise InternalError(message=f"Database error: {e}")
    if aeroplane is None:
        raise NotFoundError(entity="Aeroplane", resource_id=aeroplane_uuid)
    return aeroplane


def generate_avl_content(db: Session, aeroplane_uuid) -> str:
    """Generate AVL geometry content from the current aeroplane state.

    Uses lazy imports for aerosandbox to tolerate platforms where it is unavailable.
    """
    import aerosandbox as asb

    from app.converters.model_schema_converters import aeroplane_schema_to_asb_airplane_async
    from app.services.analysis_service import get_aeroplane_schema_or_raise

    plane_schema = get_aeroplane_schema_or_raise(db, aeroplane_uuid)
    asb_airplane = aeroplane_schema_to_asb_airplane_async(plane_schema=plane_schema)

    op_point = asb.OperatingPoint(velocity=10, alpha=0)
    avl = asb.AVL(airplane=asb_airplane, op_point=op_point)

    with tempfile.TemporaryDirectory() as tmp_dir:
        avl_path = Path(tmp_dir) / "airplane.avl"
        avl.write_avl(avl_path)
        return avl_path.read_text()


def get_avl_geometry(db: Session, aeroplane_uuid) -> AvlGeometryResponse:
    """Return the stored AVL geometry file, or generate it on the fly if none exists."""
    aeroplane = _get_aeroplane_or_raise(db, aeroplane_uuid)

    geom = (
        db.query(AvlGeometryFileModel)
        .filter_by(aeroplane_id=aeroplane.id)
        .first()
    )
    if geom is not None:
        return AvlGeometryResponse(
            content=geom.content,
            is_dirty=geom.is_dirty,
            is_user_edited=geom.is_user_edited,
        )

    content = generate_avl_content(db, aeroplane_uuid)
    return AvlGeometryResponse(
        content=content,
        is_dirty=False,
        is_user_edited=False,
    )


def save_avl_geometry(db: Session, aeroplane_uuid, content: str) -> AvlGeometryResponse:
    """Persist user-edited AVL geometry content, creating or updating the record."""
    aeroplane = _get_aeroplane_or_raise(db, aeroplane_uuid)

    geom = (
        db.query(AvlGeometryFileModel)
        .filter_by(aeroplane_id=aeroplane.id)
        .first()
    )
    if geom is None:
        geom = AvlGeometryFileModel(aeroplane_id=aeroplane.id, content=content)
        db.add(geom)
    else:
        geom.content = content

    geom.is_user_edited = True
    geom.is_dirty = False
    db.flush()

    return AvlGeometryResponse(
        content=geom.content,
        is_dirty=geom.is_dirty,
        is_user_edited=geom.is_user_edited,
    )


def regenerate_avl_geometry(db: Session, aeroplane_uuid) -> AvlGeometryResponse:
    """Discard any saved file and regenerate content from the current aeroplane state."""
    _get_aeroplane_or_raise(db, aeroplane_uuid)
    content = generate_avl_content(db, aeroplane_uuid)
    return AvlGeometryResponse(
        content=content,
        is_dirty=False,
        is_user_edited=False,
    )


def delete_avl_geometry(db: Session, aeroplane_uuid) -> None:
    """Delete the stored AVL geometry file. Raises NotFoundError if none exists."""
    aeroplane = _get_aeroplane_or_raise(db, aeroplane_uuid)

    geom = (
        db.query(AvlGeometryFileModel)
        .filter_by(aeroplane_id=aeroplane.id)
        .first()
    )
    if geom is None:
        raise NotFoundError(entity="AVL geometry file", resource_id=aeroplane_uuid)

    db.delete(geom)
    db.flush()
