"""Construction Parts service (gh#57-g4h + gh#57-9uk).

D1 (g4h): list, get, lock, unlock.
D2 (9uk): create with multipart upload, file download (with optional
STEP→STL regeneration), metadata update, lock-protected delete, +
geometry extraction via CadQuery at upload time.
"""
from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    InternalError,
    NotFoundError,
    ValidationError,
)
from app.core.platform import cad_available
from app.models.construction_part import ConstructionPartModel
from app.schemas.construction_part import (
    ConstructionPartList,
    ConstructionPartRead,
    ConstructionPartUpdate,
)

logger = logging.getLogger(__name__)

ALLOWED_SUFFIXES = {".step", ".stp", ".stl"}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
ALLOWED_DOWNLOAD_FORMATS = {"step", "stl"}
STORAGE_ROOT = Path("tmp") / "construction_parts"


def _get_part_or_404(
    db: Session, aeroplane_id: str, part_id: int
) -> ConstructionPartModel:
    """Fetch a part by (aeroplane_id, id). Raises NotFoundError if either check fails.

    Aeroplane scoping is enforced here so that callers cannot cross-access a
    part that belongs to a different aeroplane by guessing its ID.
    """
    part = (
        db.query(ConstructionPartModel)
        .filter(
            ConstructionPartModel.id == part_id,
            ConstructionPartModel.aeroplane_id == aeroplane_id,
        )
        .first()
    )
    if part is None:
        raise NotFoundError(entity="ConstructionPart", resource_id=part_id)
    return part


def list_parts(db: Session, aeroplane_id: str) -> ConstructionPartList:
    rows = (
        db.query(ConstructionPartModel)
        .filter(ConstructionPartModel.aeroplane_id == aeroplane_id)
        .order_by(ConstructionPartModel.name)
        .all()
    )
    return ConstructionPartList(
        aeroplane_id=aeroplane_id,
        items=[ConstructionPartRead.model_validate(r) for r in rows],
        total=len(rows),
    )


def get_part(db: Session, aeroplane_id: str, part_id: int) -> ConstructionPartRead:
    part = _get_part_or_404(db, aeroplane_id, part_id)
    return ConstructionPartRead.model_validate(part)


def _set_locked(
    db: Session, aeroplane_id: str, part_id: int, locked: bool
) -> ConstructionPartRead:
    try:
        part = _get_part_or_404(db, aeroplane_id, part_id)
        part.locked = locked
        db.flush()
        db.refresh(part)
        return ConstructionPartRead.model_validate(part)
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error while toggling lock on part %s: %s", part_id, exc)
        raise InternalError(message=f"Database error: {exc}") from exc


def lock_part(db: Session, aeroplane_id: str, part_id: int) -> ConstructionPartRead:
    """Set locked=True. Idempotent when the part is already locked."""
    return _set_locked(db, aeroplane_id, part_id, True)


def unlock_part(db: Session, aeroplane_id: str, part_id: int) -> ConstructionPartRead:
    """Set locked=False. Idempotent when the part is already unlocked."""
    return _set_locked(db, aeroplane_id, part_id, False)


# --------------------------------------------------------------------------- #
# D2 (9uk): Upload, Download, Update, Delete
# --------------------------------------------------------------------------- #


def _validate_upload(filename: Optional[str], content: bytes) -> tuple[str, str]:
    """Return (suffix_lower, format) or raise ValidationError / ConflictError.

    ValidationError = unsupported / empty.
    The size check uses ConflictError-mapped HTTP 413 via the endpoint layer.
    """
    if not content:
        raise ValidationError(message="Uploaded file is empty.")
    if len(content) > MAX_FILE_SIZE_BYTES:
        # Marker for the endpoint to map to 413.
        raise ConflictError(
            message=(
                f"File exceeds maximum size of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
            ),
            details={"reason": "file_too_large"},
        )
    suffix = Path(filename or "upload.unknown").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ValidationError(
            message=(
                f"Unsupported file extension '{suffix}'. "
                f"Allowed: {sorted(ALLOWED_SUFFIXES)}"
            ),
        )
    fmt = "stl" if suffix == ".stl" else "step"
    return suffix, fmt


def _store_file(aeroplane_id: str, part_id: int, content: bytes, suffix: str) -> Path:
    """Persist the uploaded bytes under tmp/construction_parts/{aeroplane}/."""
    target_dir = STORAGE_ROOT / aeroplane_id
    target_dir.mkdir(parents=True, exist_ok=True)
    dest = target_dir / f"{part_id}_{uuid4().hex[:8]}{suffix}"
    with dest.open("wb") as out:
        out.write(content)
    return dest


def _extract_geometry(file_path: Path, file_format: str) -> dict[str, Optional[float]]:
    """Return geometry metadata from the uploaded file via CadQuery.

    Returns a dict with volume_mm3, area_mm2, bbox_x_mm/y/z. Returns all-None
    when CadQuery is unavailable (linux/aarch64) or extraction fails — the
    upload still succeeds with NULL geometry fields.
    """
    empty = {
        "volume_mm3": None,
        "area_mm2": None,
        "bbox_x_mm": None,
        "bbox_y_mm": None,
        "bbox_z_mm": None,
    }
    if not cad_available():
        return empty
    if file_format != "step":
        # STL meshes do not give us a watertight solid; computing volume from
        # a triangle soup needs extra dependencies (numpy-stl etc.). For MVP
        # we leave STL geometry NULL and document the limitation. Users who
        # need geometry should upload STEP.
        logger.info(
            "Skipping geometry extraction for non-STEP format '%s' on %s",
            file_format, file_path,
        )
        return empty
    try:
        import cadquery as cq

        shape = cq.importers.importStep(str(file_path))
        wp_val = shape.val()
        try:
            volume = float(wp_val.Volume())
        except Exception:  # noqa: BLE001 — degenerate shapes are OK
            volume = None
        try:
            area = float(wp_val.Area())
        except Exception:  # noqa: BLE001
            area = None
        try:
            bb = wp_val.BoundingBox()
            bbox = (float(bb.xlen), float(bb.ylen), float(bb.zlen))
        except Exception:  # noqa: BLE001
            bbox = (None, None, None)
        return {
            "volume_mm3": volume,
            "area_mm2": area,
            "bbox_x_mm": bbox[0],
            "bbox_y_mm": bbox[1],
            "bbox_z_mm": bbox[2],
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Geometry extraction failed for %s: %s", file_path, exc)
        return empty


def create_part(
    db: Session,
    aeroplane_id: str,
    *,
    filename: Optional[str],
    content: bytes,
    name: str,
    material_component_id: Optional[int],
    thumbnail_url: Optional[str],
) -> ConstructionPartRead:
    """Upload a STEP/STL file and persist a new construction-part row.

    Aeroplane-scoped. Geometry is extracted at upload (NULL if CadQuery
    unavailable). The file is stored under
    ``tmp/construction_parts/{aeroplane_id}/{part_id}_{uuid8}{ext}``.
    """
    suffix, fmt = _validate_upload(filename, content)
    if not name or not name.strip():
        raise ValidationError(message="name is required.")

    try:
        # Two-phase: insert row to get an ID, then store file using the ID.
        part = ConstructionPartModel(
            aeroplane_id=aeroplane_id,
            name=name.strip(),
            material_component_id=material_component_id,
            thumbnail_url=thumbnail_url,
            file_format=fmt,
            locked=False,
        )
        db.add(part)
        db.flush()  # populate part.id without committing the transaction yet
        dest = _store_file(aeroplane_id, part.id, content, suffix)
        part.file_path = str(dest)
        geom = _extract_geometry(dest, fmt)
        for key, value in geom.items():
            setattr(part, key, value)
        db.flush()
        db.refresh(part)
        return ConstructionPartRead.model_validate(part)
    except ValidationError:
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in create_part: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc


def get_part_file(
    db: Session, aeroplane_id: str, part_id: int, fmt: str
) -> tuple[Path, str]:
    """Return (path_to_serve, mime_type) for the requested format.

    Raises ValidationError when the format is invalid or cannot be produced
    (e.g. STEP requested but source is STL).
    """
    if fmt not in ALLOWED_DOWNLOAD_FORMATS:
        raise ValidationError(
            message=f"Invalid format '{fmt}'. Allowed: {sorted(ALLOWED_DOWNLOAD_FORMATS)}",
        )
    part = _get_part_or_404(db, aeroplane_id, part_id)
    if not part.file_path:
        raise NotFoundError(entity="ConstructionPart file", resource_id=part_id)

    source_path = Path(part.file_path)
    source_format = part.file_format

    if fmt == source_format:
        return source_path, ("model/stl" if fmt == "stl" else "model/step")

    if fmt == "stl" and source_format == "step":
        # Regenerate STL from STEP via CadQuery on the fly.
        if not cad_available():
            raise ValidationError(
                message="STL regeneration requires CadQuery, which is unavailable on this platform.",
            )
        import cadquery as cq

        tmp_stl = Path(tempfile.mkstemp(suffix=".stl")[1])
        try:
            shape = cq.importers.importStep(str(source_path))
            cq.exporters.export(shape, str(tmp_stl), exportType="STL")
            return tmp_stl, "model/stl"
        except Exception as exc:  # noqa: BLE001
            logger.error("STL regeneration failed for part %s: %s", part_id, exc)
            raise InternalError(message=f"STL regeneration failed: {exc}") from exc

    if fmt == "step" and source_format == "stl":
        raise ValidationError(
            message="Source is STL — STEP cannot be regenerated from STL.",
        )

    raise ValidationError(
        message=f"Cannot serve format '{fmt}' for source format '{source_format}'.",
    )


def update_part(
    db: Session,
    aeroplane_id: str,
    part_id: int,
    data: ConstructionPartUpdate,
) -> ConstructionPartRead:
    """Update name / material / thumbnail. File and geometry are NOT touched."""
    try:
        part = _get_part_or_404(db, aeroplane_id, part_id)
        explicit = data.model_dump(exclude_unset=True)
        if "name" in explicit and explicit["name"]:
            part.name = explicit["name"].strip()
        if "material_component_id" in explicit:
            part.material_component_id = explicit["material_component_id"]
        if "thumbnail_url" in explicit:
            part.thumbnail_url = explicit["thumbnail_url"]
        db.flush()
        db.refresh(part)
        return ConstructionPartRead.model_validate(part)
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in update_part: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc


def delete_part(db: Session, aeroplane_id: str, part_id: int) -> None:
    """Delete a part and remove its file. Blocks with ConflictError if locked."""
    try:
        part = _get_part_or_404(db, aeroplane_id, part_id)
        if part.locked:
            raise ConflictError(
                message=(
                    f"ConstructionPart {part_id} is locked and cannot be deleted. "
                    "Unlock it first."
                ),
                details={"part_id": part_id},
            )
        file_path = part.file_path
        db.delete(part)
        db.flush()
        if file_path:
            # NOTE: File is unlinked before get_db() commits the DB deletion.
            # If the commit fails, the DB row will reference a missing file.
            # Acceptable trade-off: the alternative (delete after commit) risks
            # orphaned files if the app crashes between commit and unlink.
            try:
                os.unlink(file_path)
            except FileNotFoundError:
                # File already gone — log but don't fail the request, the DB
                # row deletion is the source of truth.
                logger.info("File for part %s already missing: %s", part_id, file_path)
    except (NotFoundError, ConflictError):
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in delete_part: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc
