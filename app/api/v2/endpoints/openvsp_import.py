"""REST endpoint for the OpenVSP `.vsp3` importer (gh-646).

POST ``/api/v2/import/openvsp`` accepts a multipart upload, parses
it via :func:`app.services.openvsp_import_service.import_openvsp_file`,
and returns a JSON envelope with the created aeroplane uuid plus
any import warnings.

Returns:

* **201** with response body when the import succeeds (even with
  warnings).
* **400** when the uploaded file isn't ``.vsp3``.
* **413** when the upload exceeds the size cap.
* **422** when the file is malformed.
* **503** when the optional ``openvsp`` package isn't installed.
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import openvsp_import_service

logger = logging.getLogger(__name__)

router = APIRouter()


# 50 MB default cap; configurable via the standard FastAPI config later.
_MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024


class ImportWarningResponse(BaseModel):
    component_type: str
    component_name: str
    reason: str
    severity: str


class OpenVspImportResponseModel(BaseModel):
    aeroplane_uuid: str = Field(..., description="UUID of the created aeroplane")
    aeroplane_name: str = Field(..., description="Name of the created aeroplane")
    n_wings: int = Field(..., description="Number of wings imported")
    n_fuselages: int = Field(..., description="Number of fuselages imported")
    n_weight_items: int = Field(
        ..., description="Number of weight items parsed (not yet persisted in Phase 1)"
    )
    warnings: list[ImportWarningResponse] = Field(default_factory=list)
    lossy_components: list[str] = Field(
        default_factory=list,
        description="Component geom IDs that were dropped or partially imported",
    )


@router.post(
    "/import/openvsp",
    status_code=status.HTTP_201_CREATED,
    tags=["import"],
    operation_id="import_openvsp_vsp3",
    response_model=OpenVspImportResponseModel,
)
async def import_openvsp(
    file: Annotated[UploadFile, File(..., description="OpenVSP .vsp3 file")],
    db: Annotated[Session, Depends(get_db)],
) -> OpenVspImportResponseModel:
    """Import an OpenVSP ``.vsp3`` file as a new aeroplane.

    See :mod:`app.services.openvsp_import_service` for the parser
    contract and ``docs/md/openvsp-import-setup.md`` for installation.
    """
    if not openvsp_import_service.is_importer_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "OpenVSP Python bindings are not installed on this server. "
                "See docs/md/openvsp-import-setup.md for setup."
            ),
        )

    filename = file.filename or ""
    if not filename.lower().endswith(".vsp3"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expected a .vsp3 file upload.",
        )

    raw = await file.read()
    if len(raw) > _MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(f"Upload exceeds the {_MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB size limit."),
        )

    # Persist to a temp file so the openvsp loader can open it by path.
    # Both the temp-file write and the parser itself are blocking — run
    # them on the thread pool so the event loop stays responsive (S7493).
    def _write_temp() -> Path:
        with tempfile.NamedTemporaryFile(suffix=".vsp3", delete=False) as tmp:
            tmp.write(raw)
            return Path(tmp.name)

    tmp_path = await asyncio.to_thread(_write_temp)

    try:
        response = await asyncio.to_thread(
            openvsp_import_service.import_openvsp_file, db, tmp_path
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Temp file vanished during import: {exc}",
        ) from exc
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except Exception as exc:  # noqa: BLE001 — translate to 422 with hint
        logger.exception("OpenVSP import failed")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse OpenVSP file: {exc}",
        ) from exc
    finally:
        try:
            await asyncio.to_thread(tmp_path.unlink, missing_ok=True)
        except OSError:
            logger.warning("Could not remove temp file %s", tmp_path)

    return OpenVspImportResponseModel(
        aeroplane_uuid=response.aeroplane_uuid,
        aeroplane_name=response.aeroplane_name,
        n_wings=response.n_wings,
        n_fuselages=response.n_fuselages,
        n_weight_items=response.n_weight_items,
        warnings=[ImportWarningResponse(**w) for w in response.warnings],
        lossy_components=response.lossy_components,
    )
