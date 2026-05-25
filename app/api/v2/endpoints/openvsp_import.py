"""REST endpoint for the OpenVSP `.vsp3` importer (gh-646, scaling in gh-695).

POST ``/api/v2/import/openvsp`` accepts a multipart upload, parses
it via :func:`app.services.openvsp_import_service.import_openvsp_file`,
and returns a JSON envelope with the created aeroplane uuid plus
any import warnings.

Optional Quick-Scale query parameters (gh-695, mutually exclusive):

* ``?target_span_m=<float>`` — rescale so the largest wing physical
  span equals this value (in metres).
* ``?scale_factor=<float>`` — multiply all length-typed fields.

Returns:

* **201** with response body when the import succeeds (even with
  warnings).
* **400** when the uploaded file isn't ``.vsp3`` OR when both scaling
  params are supplied (mutex violation).
* **413** when the upload exceeds the size cap.
* **422** when the file is malformed OR scaling inputs are out of
  range / target_span_m requested with no wings.
* **503** when the optional ``openvsp`` package isn't installed.
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import openvsp_import_service
from app.services.openvsp_import_service import ScaleValidationError

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
    target_span_m: Annotated[
        Optional[float],
        Query(
            description=(
                "Optional: rescale the imported aeroplane so the largest "
                "wing physical span equals this value in metres. Mutually "
                "exclusive with scale_factor. Range: (0.1, 50)."
            ),
        ),
    ] = None,
    scale_factor: Annotated[
        Optional[float],
        Query(
            description=(
                "Optional: multiply all length-typed fields (positions, "
                "chords, fuselage radii, weight-item positions) by this "
                "factor. Mutually exclusive with target_span_m. "
                "Range: (0.001, 10). Masses are NOT scaled."
            ),
        ),
    ] = None,
    name: Annotated[
        Optional[str],
        Query(
            max_length=200,
            description=(
                "Optional: user-supplied aeroplane name. Overrides the "
                "default (which is the uploaded filename's stem). "
                "Whitespace-only values are treated as 'no override'."
            ),
        ),
    ] = None,
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

    # Mutex check is cheap and translates to 400 (request-shape error
    # — the user supplied two contradictory parameters). Out-of-range
    # checks happen inside the service and surface as 422 below.
    if target_span_m is not None and scale_factor is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "target_span_m and scale_factor are mutually exclusive; "
                "specify at most one."
            ),
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
            openvsp_import_service.import_openvsp_file,
            db,
            tmp_path,
            target_span_m=target_span_m,
            scale_factor=scale_factor,
            name=name,
            source_filename=file.filename,
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
    except ScaleValidationError as exc:
        # Out-of-range scale params / no-wings → 422 (semantic error
        # in otherwise well-formed request). Distinct from the 400
        # mutex-check above which guards request shape.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
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
