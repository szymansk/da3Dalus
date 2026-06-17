"""Service for the section-geometry endpoint (gh-1021).

Resolve an aeroplane id -> its wing -> a ``WingConfiguration`` (mm), build the
:class:`cad_designer.airplane.geometry.section_geometry.SectionGeometry`
primitive, sample it, and convert the millimetre results to metres for the API.

The ``SectionGeometry`` construction needs cadquery (excluded on
``linux/aarch64``). When unavailable it raises
``SectionGeometryUnavailableError``; we translate that into a ``ValidationError``
so the endpoint returns a clean 422 instead of crashing.
"""

from __future__ import annotations

import logging

import numpy as np

from app.converters.model_schema_converters import wing_model_to_wing_config
from app.core.exceptions import NotFoundError, ValidationError
from app.schemas.section_geometry import (
    SectionGeometryRequest,
    SectionGeometryResponse,
    SectionPointOut,
)
from app.services.wing_service import get_aeroplane_or_raise, get_wing_or_raise

logger = logging.getLogger(__name__)

_MM_TO_M = 0.001

# Default grid resolution when the caller omits the sample arrays.
_DEFAULT_N_SPAN = 11
_DEFAULT_N_CHORD = 11
# Per-segment default grid resolution.
_DEFAULT_SEGMENT_N_SPAN = 5
_DEFAULT_SEGMENT_N_CHORD = 11


def _default_grid(n: int) -> list[float]:
    """Evenly spaced fractions over the open-ended (0, 1] interior.

    We avoid the exact endpoints (0.0 / 1.0) so samples land on the section
    interior, where the chord ordinate reliably intersects the outline.
    """
    return [round(float(v), 6) for v in np.linspace(0.0, 1.0, n + 2)[1:-1]]


def _to_out(point) -> SectionPointOut:
    """Convert a millimetre ``SectionPoint`` to a metre ``SectionPointOut``."""
    return SectionPointOut(
        y_span=point.y_span,
        x_c=point.x_c,
        thickness=point.thickness * _MM_TO_M,
        top_z=point.top_z * _MM_TO_M,
        bottom_z=point.bottom_z * _MM_TO_M,
        center_z=point.center_z * _MM_TO_M,
    )


def _build_section_geometry(wing_config):
    """Construct the SectionGeometry primitive, translating the platform guard.

    Kept as a thin seam so fast tests can monkeypatch the cadquery boundary.
    """
    from cad_designer.airplane.geometry.section_geometry import (
        SectionGeometry,
        SectionGeometryUnavailableError,
    )

    try:
        return SectionGeometry(wing_config)
    except SectionGeometryUnavailableError as exc:
        raise ValidationError(
            message=f"Section geometry is unavailable on this platform: {exc}",
        ) from exc


def compute_section_geometry(
    db,
    aeroplane_uuid,
    request: SectionGeometryRequest,
) -> SectionGeometryResponse:
    """Sample the built section geometry of an aeroplane's wing.

    Raises:
        NotFoundError: aeroplane or wing does not exist (-> 404).
        ValidationError: section geometry unavailable on this platform (-> 422).
    """
    aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)

    if request.wing_name is not None:
        wing = get_wing_or_raise(aeroplane, request.wing_name)
    else:
        if not aeroplane.wings:
            raise NotFoundError(
                message="Aeroplane has no wings to query section geometry for",
                details={"aeroplane_id": str(aeroplane_uuid)},
            )
        wing = aeroplane.wings[0]

    # WingConfiguration / SectionGeometry work in millimetres (scale=1000.0).
    wing_config = wing_model_to_wing_config(wing, scale=1000.0)

    geometry = _build_section_geometry(wing_config)

    y_spans = request.y_over_span or _default_grid(_DEFAULT_N_SPAN)
    x_cs = request.x_over_chord or _default_grid(_DEFAULT_N_CHORD)

    surface = [_to_out(p) for p in geometry.sample(y_spans, x_cs)]

    segments = None
    if request.per_segment:
        per_seg = geometry.per_segment(_DEFAULT_SEGMENT_N_SPAN, _DEFAULT_SEGMENT_N_CHORD)
        segments = {idx: [_to_out(p) for p in points] for idx, points in per_seg.items()}

    return SectionGeometryResponse(surface=surface, segments=segments)
