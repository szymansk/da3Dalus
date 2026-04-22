"""Fuselage Slice Service — orchestrates STEP upload, slicing, and response."""

import logging
import shutil
import tempfile
from pathlib import Path
from uuid import uuid4

from app.core.exceptions import InternalError, ValidationError
from app.schemas.aeroplaneschema import FuselageSchema, FuselageXSecSuperEllipseSchema
from app.schemas.fuselage_slice import (
    FidelityMetrics,
    FuselageSliceResponse,
    GeometryProperties,
)

logger = logging.getLogger(__name__)


def slice_step_file(
    file_content: bytes,
    filename: str,
    number_of_slices: int = 50,
    points_per_slice: int = 30,
    slice_axis: str = "auto",
    fuselage_name: str = "Imported Fuselage",
) -> FuselageSliceResponse:
    """Slice a STEP file into a FuselageSchema with fidelity metrics.

    This is CPU-bound work (CadQuery + scipy optimization) and may take
    5-30 seconds depending on model complexity and slice count.
    """
    # Lazy import — CadQuery not available on all platforms
    try:
        from cad_designer.aerosandbox.slicing import slice_step_to_fuselage
    except ImportError as exc:
        raise InternalError(
            message="CadQuery is not available on this platform. "
                    "Fuselage slicing requires CadQuery + OCP."
        ) from exc

    # Sanitize filename: strip any path components to prevent path traversal (S2083)
    safe_name = Path(filename).name  # basename only, no directory components
    suffix = Path(safe_name).suffix.lower()
    if suffix not in (".step", ".stp"):
        raise ValidationError(
            message=f"Unsupported file type: {suffix}. Only STEP files (.step, .stp) are supported."
        )

    # Write to temp file (CadQuery needs a file path)
    tmp_dir = Path(tempfile.mkdtemp(prefix="fuselage_slice_"))
    tmp_file = tmp_dir / f"upload{suffix}"
    # Verify the resolved path stays within the temp directory
    if not tmp_file.resolve().is_relative_to(tmp_dir.resolve()):
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise ValidationError(message="Invalid filename: path traversal detected.")
    tmp_file.write_bytes(file_content)

    try:
        xsecs, metrics = slice_step_to_fuselage(
            step_path=str(tmp_file),
            number_of_slices=number_of_slices,
            points_per_slice=points_per_slice,
            slice_axis=slice_axis,
            fuselage_name=fuselage_name,
        )
    except FileNotFoundError as exc:
        raise ValidationError(message=f"STEP file processing failed: {exc}") from exc
    except Exception as exc:
        logger.error("Slicing failed: %s", exc)
        raise InternalError(message=f"Fuselage slicing failed: {exc}") from exc
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # Convert to FuselageSchema
    fuselage_xsecs = [
        FuselageXSecSuperEllipseSchema(
            xyz=xsec["xyz"],
            a=xsec["a"],
            b=xsec["b"],
            n=xsec["n"],
        )
        for xsec in xsecs
    ]

    fuselage = FuselageSchema(name=fuselage_name, x_secs=fuselage_xsecs)

    return FuselageSliceResponse(
        fuselage=fuselage,
        original_properties=GeometryProperties(
            volume_m3=metrics["original_volume"],
            surface_area_m2=metrics["original_area"],
        ),
        reconstructed_properties=GeometryProperties(
            volume_m3=metrics["reconstructed_volume"],
            surface_area_m2=metrics["reconstructed_area"],
        ),
        fidelity=FidelityMetrics(
            volume_ratio=metrics["volume_ratio"],
            area_ratio=metrics["area_ratio"],
        ),
        # Tessellation URLs will be added when STL export is wired
        original_tessellation_url=None,
        reconstructed_tessellation_url=None,
    )
