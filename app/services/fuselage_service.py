"""
Fuselage Service - Business logic for fuselage and cross-section operations.

This module contains the core logic for fuselage management,
separated from HTTP concerns for better testability and reusability.
"""

import json
import logging
from datetime import datetime
from typing import List

from aero_kernel.body_attachment import AttachedBody, AttachmentDefect, attachment_defects
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import schemas
from app.core.exceptions import ConflictError, InternalError, NotFoundError, ValidationError
from app.models.aeroplanemodel import (
    AeroplaneModel,
    FuselageModel,
    FuselageXSecSuperEllipseModel,
)
from app.schemas.fuselage_contour import canon_threshold, contour_set_messages
from app.services.wing_service import get_aeroplane_or_raise

logger = logging.getLogger(__name__)

# --- Shared error messages (S1192) ---
_ERR_FUSELAGE_NOT_FOUND = "Fuselage not found"
_ERR_XSEC_NOT_FOUND = "Cross-section not found"


def _get_fuselage_or_raise(aeroplane: AeroplaneModel, fuselage_name: str) -> FuselageModel:
    """Get a fuselage by name from an aeroplane or raise NotFoundError."""
    fuselage = next((f for f in aeroplane.fuselages if f.name == fuselage_name), None)
    if not fuselage:
        raise NotFoundError(
            message=_ERR_FUSELAGE_NOT_FOUND,
            details={
                "fuselage_name": fuselage_name,
                "aeroplane_id": str(aeroplane.uuid),
            },
        )
    return fuselage


def _attached_bodies(aeroplane: AeroplaneModel) -> dict[str, AttachedBody]:
    """What the attachment rules read of every body of the aeroplane, by name (gh-1355)."""
    return {
        f.name: AttachedBody(
            # a body not flushed yet has no column default applied; the format's default is
            # fuselage (the schema always sets it, so this only covers hand-built models)
            role=f.role if f.role is not None else "fuselage",
            attached_to=f.attached_to,
            x=tuple(float(xs.xyz[0]) for xs in f.x_secs),
        )
        for f in aeroplane.fuselages
    }


def _attachment_path(defect: AttachmentDefect) -> str:
    """The input path of an attachment defect, e.g. ``fuselages["Canopy"].attached_to``."""
    path = f"fuselages[{json.dumps(defect.body, ensure_ascii=False)}]"
    if defect.section is None:
        return f"{path}.attached_to"
    return f"{path}.x_secs[{defect.section}].xyz[0]"


def _ensure_attachments_valid(aeroplane: AeroplaneModel) -> None:
    """Refuse a change that breaks the role / attached_to rules of the bodies (gh-1355).

    Runs on the aeroplane's bodies as they would be after the change, with the aero kernel's
    rules (canon rule ``body-attachment``), so a document the API accepts is one the kernel
    accepts. Raises ``ValidationError`` (422) naming every offending path; nothing is repaired.
    """
    minimum = int(canon_threshold("minimum-sections", "min_sections"))
    defects = attachment_defects(_attached_bodies(aeroplane), minimum)
    if not defects:
        return
    paths = [_attachment_path(defect) for defect in defects]
    raise ValidationError(
        message="; ".join(f"{path}: {d.message}" for path, d in zip(paths, defects, strict=True)),
        details={"input_path": paths[0], "code": defects[0].code},
    )


def _ensure_nothing_attached(aeroplane: AeroplaneModel, fuselage_name: str) -> None:
    """Refuse to delete a body that others sit on: their attached_to would dangle (gh-1355)."""
    children = [f.name for f in aeroplane.fuselages if f.attached_to == fuselage_name]
    if children:
        raise ConflictError(
            message=(
                f"Fuselage {fuselage_name!r} cannot be deleted: "
                f"{', '.join(repr(c) for c in children)} attached_to it. Delete them or attach "
                "them to another body first."
            ),
            details={"fuselage_name": fuselage_name, "attached": children},
        )


def list_fuselage_names(db: Session, aeroplane_uuid) -> List[str]:
    """
    Get list of fuselage names for an aeroplane.

    Raises:
        NotFoundError: If the aeroplane does not exist.
        InternalError: If a database error occurs.
    """
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        return [f.name for f in aeroplane.fuselages]
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error("Database error when getting aeroplane fuselages: %s", e)
        raise InternalError(message=f"Database error: {e}")


def create_fuselage(
    db: Session,
    aeroplane_uuid,
    fuselage_name: str,
    fuselage_data: schemas.FuselageSchema,
) -> None:
    """
    Create a new fuselage for an aeroplane.

    Raises:
        NotFoundError: If the aeroplane does not exist.
        ConflictError: If the fuselage name already exists.
        InternalError: If a database error occurs.
    """
    try:
        plane = get_aeroplane_or_raise(db, aeroplane_uuid)

        if any(f.name == fuselage_name for f in plane.fuselages):
            raise ConflictError(
                message="Fuselage name must be unique for this aeroplane",
                details={"fuselage_name": fuselage_name},
            )

        fuselage = FuselageModel.from_dict(name=fuselage_name, data=fuselage_data.model_dump())
        plane.fuselages.append(fuselage)
        _ensure_attachments_valid(plane)
        db.add(fuselage)
        plane.updated_at = datetime.now()

        # Auto-sync: create group in component tree (gh#108)
        from app.services.component_tree_service import sync_group_for_fuselage

        sync_group_for_fuselage(db, str(aeroplane_uuid), fuselage_name)
        db.flush()
    except (NotFoundError, ConflictError, ValidationError):
        raise
    except SQLAlchemyError as e:
        logger.error("Database error when creating aeroplane fuselage: %s", e)
        raise InternalError(message=f"Database error: {e}")


def update_fuselage(
    db: Session,
    aeroplane_uuid,
    fuselage_name: str,
    fuselage_data: schemas.FuselageSchema,
) -> None:
    """
    Overwrite an existing fuselage with new data.

    Raises:
        NotFoundError: If the aeroplane or fuselage does not exist.
        InternalError: If a database error occurs.
    """
    try:
        plane = get_aeroplane_or_raise(db, aeroplane_uuid)
        fuselage = _get_fuselage_or_raise(plane, fuselage_name)

        new_fuselage = FuselageModel.from_dict(name=fuselage_name, data=fuselage_data.model_dump())
        plane.fuselages.remove(fuselage)
        plane.fuselages.append(new_fuselage)
        _ensure_attachments_valid(plane)
        plane.updated_at = datetime.now()

        # Auto-sync: ensure group exists in component tree (gh#108)
        from app.services.component_tree_service import sync_group_for_fuselage

        sync_group_for_fuselage(db, str(aeroplane_uuid), fuselage_name)
        db.flush()
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error("DB error updating fuselage: %s", e)
        raise InternalError(message=f"Database error: {e}")


def get_fuselage(
    db: Session,
    aeroplane_uuid,
    fuselage_name: str,
) -> schemas.FuselageSchema:
    """
    Get a fuselage as schema.

    Raises:
        NotFoundError: If the aeroplane or fuselage does not exist.
        InternalError: If a database error occurs.
    """
    try:
        plane = get_aeroplane_or_raise(db, aeroplane_uuid)
        fuselage = _get_fuselage_or_raise(plane, fuselage_name)
        return schemas.FuselageSchema.model_validate(fuselage, from_attributes=True)
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error("Database error when getting aeroplane fuselage: %s", e)
        raise InternalError(message=f"Database error: {e}")


def delete_fuselage(
    db: Session,
    aeroplane_uuid,
    fuselage_name: str,
) -> None:
    """
    Delete a fuselage.

    Raises:
        NotFoundError: If the aeroplane or fuselage does not exist.
        InternalError: If a database error occurs.
    """
    try:
        plane = get_aeroplane_or_raise(db, aeroplane_uuid)
        fuselage = _get_fuselage_or_raise(plane, fuselage_name)
        _ensure_nothing_attached(plane, fuselage_name)
        db.delete(fuselage)
        plane.updated_at = datetime.now()

        # Auto-sync: remove fuselage group from component tree (gh#108)
        from app.services.component_tree_service import delete_synced_nodes

        delete_synced_nodes(db, str(aeroplane_uuid), f"fuselage:{fuselage_name}")
        db.flush()
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error("Database error when deleting aeroplane fuselage: %s", e)
        raise InternalError(message=f"Database error: {e}")


# --- Cross-section operations ---


def _ensure_contours_consistent(contours: list, fuselage_name: str) -> None:
    """Refuse a single-section change that would break the fuselage's all-or-none contour rule.

    The whole-fuselage writes are checked by ``FuselageSchema``; a create or update of one
    section is checked here against its siblings (gh-1349). Raises ``ValidationError`` (422)
    with the ``input_path`` of the first offending section.
    """
    messages = contour_set_messages(contours)
    if messages:
        index, message = messages[0]
        raise ValidationError(
            message=f"Fuselage {fuselage_name!r}: {message}",
            details={"input_path": f"x_secs[{index}].contour", "fuselage_name": fuselage_name},
        )


def get_fuselage_cross_sections(
    db: Session,
    aeroplane_uuid,
    fuselage_name: str,
) -> List[schemas.FuselageXSecSuperEllipseSchema]:
    """
    Get all cross-sections for a fuselage.

    Raises:
        NotFoundError: If the aeroplane or fuselage does not exist.
        InternalError: If a database error occurs.
    """
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        fuselage = _get_fuselage_or_raise(aeroplane, fuselage_name)
        return [
            schemas.FuselageXSecSuperEllipseSchema.model_validate(xs, from_attributes=True)
            for xs in fuselage.x_secs
        ]
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error("Database error when getting fuselage cross-sections: %s", e)
        raise InternalError(message=f"Database error: {e}")


def delete_all_cross_sections(
    db: Session,
    aeroplane_uuid,
    fuselage_name: str,
) -> None:
    """
    Delete all cross-sections from a fuselage.

    Raises:
        NotFoundError: If the aeroplane or fuselage does not exist.
        InternalError: If a database error occurs.
    """
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        fuselage = _get_fuselage_or_raise(aeroplane, fuselage_name)
        fuselage.x_secs.clear()
        aeroplane.updated_at = datetime.now()
        db.flush()
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error("Database error when deleting fuselage cross-sections: %s", e)
        raise InternalError(message=f"Database error: {e}")


def get_cross_section(
    db: Session,
    aeroplane_uuid,
    fuselage_name: str,
    index: int,
) -> schemas.FuselageXSecSuperEllipseSchema:
    """
    Get a specific cross-section by index.

    Raises:
        NotFoundError: If the aeroplane, fuselage, or cross-section does not exist.
        InternalError: If a database error occurs.
    """
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        fuselage = _get_fuselage_or_raise(aeroplane, fuselage_name)
        x_secs = fuselage.x_secs
        if index < 0 or index >= len(x_secs):
            raise NotFoundError(
                message=_ERR_XSEC_NOT_FOUND,
                details={"index": index, "fuselage_name": fuselage_name},
            )
        return schemas.FuselageXSecSuperEllipseSchema.model_validate(
            x_secs[index], from_attributes=True
        )
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error("Database error when getting fuselage cross-section: %s", e)
        raise InternalError(message=f"Database error: {e}")


def create_cross_section(
    db: Session,
    aeroplane_uuid,
    fuselage_name: str,
    index: int,
    xsec_data: schemas.FuselageXSecSuperEllipseSchema,
) -> None:
    """
    Create a new cross-section at the specified index.

    An index of -1 or beyond the current list length appends to the end.

    Raises:
        NotFoundError: If the aeroplane or fuselage does not exist.
        InternalError: If a database error occurs.
    """
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        fuselage = _get_fuselage_or_raise(aeroplane, fuselage_name)

        data = xsec_data.model_dump()
        existing = fuselage.x_secs

        if index == -1 or index >= len(existing):
            insertion_index = len(existing)
        else:
            insertion_index = index

        contours = [xs.contour for xs in existing]
        contours.insert(insertion_index, data["contour"])
        _ensure_contours_consistent(contours, fuselage_name)

        # Shift sort_index of following cross-sections
        for xs in existing[insertion_index:]:
            xs.sort_index = xs.sort_index + 1
            db.add(xs)

        # Create new cross-section with appropriate sort_index
        new_xsec = FuselageXSecSuperEllipseModel(sort_index=insertion_index, **data)

        if insertion_index == len(existing):
            fuselage.x_secs.append(new_xsec)
        else:
            fuselage.x_secs.insert(insertion_index, new_xsec)
        _ensure_attachments_valid(aeroplane)

        aeroplane.updated_at = datetime.now()
        db.add(new_xsec)
        db.flush()
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error("Database error when creating fuselage cross-section: %s", e)
        raise InternalError(message=f"Database error: {e}")


def update_cross_section(
    db: Session,
    aeroplane_uuid,
    fuselage_name: str,
    index: int,
    xsec_data: schemas.FuselageXSecSuperEllipseSchema,
) -> None:
    """
    Update an existing cross-section at the specified index.

    Raises:
        NotFoundError: If the aeroplane, fuselage, or cross-section does not exist.
        InternalError: If a database error occurs.
    """
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        fuselage = _get_fuselage_or_raise(aeroplane, fuselage_name)
        x_secs = fuselage.x_secs

        if index < 0 or index >= len(x_secs):
            raise NotFoundError(
                message=_ERR_XSEC_NOT_FOUND,
                details={"index": index, "fuselage_name": fuselage_name},
            )

        data = xsec_data.model_dump()
        contours = [xs.contour for xs in x_secs]
        contours[index] = data["contour"]
        _ensure_contours_consistent(contours, fuselage_name)
        new_xsec = FuselageXSecSuperEllipseModel(sort_index=index, **data)
        fuselage.x_secs[index] = new_xsec
        _ensure_attachments_valid(aeroplane)
        aeroplane.updated_at = datetime.now()
        db.flush()
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error("Database error when updating fuselage cross-section: %s", e)
        raise InternalError(message=f"Database error: {e}")


def delete_cross_section(
    db: Session,
    aeroplane_uuid,
    fuselage_name: str,
    index: int,
) -> None:
    """
    Delete a cross-section at the specified index.

    Raises:
        NotFoundError: If the aeroplane, fuselage, or cross-section does not exist.
        InternalError: If a database error occurs.
    """
    try:
        aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
        fuselage = _get_fuselage_or_raise(aeroplane, fuselage_name)
        x_secs = fuselage.x_secs

        if index < 0 or index >= len(x_secs):
            raise NotFoundError(
                message=_ERR_XSEC_NOT_FOUND,
                details={"index": index, "fuselage_name": fuselage_name},
            )

        xsec = x_secs.pop(index)
        _ensure_attachments_valid(aeroplane)
        db.delete(xsec)

        # Update sort_index for remaining cross-sections
        for i, xs in enumerate(x_secs):
            if xs.sort_index != i:
                xs.sort_index = i
                db.add(xs)

        aeroplane.updated_at = datetime.now()
        db.flush()
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error("Database error when deleting fuselage cross-section: %s", e)
        raise InternalError(message=f"Database error: {e}")
