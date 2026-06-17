"""Real local section thickness from the lofted CAD solid (gh-1022).

Wires the :class:`~cad_designer.airplane.geometry.section_geometry.SectionGeometry`
primitive (gh-1020) into spar sizing. For a wing surface and a list of spanwise
load stations (``y_m``, root = 0), this builds the lofted solid **once** and
queries the *max-thickness* chord location at each station, returning per-station
geometry maps the spar orchestrator turns into ``tc_by_y``:

* ``thickness_by_y`` — ``{y_m: built section thickness (mm)}`` at the deepest
  chord location of each station's section.
* ``center_z_by_y`` — ``{y_m: section mid-height (mm), wing-local frame}`` for
  spar placement.

Graceful degradation: when ``cadquery`` is unavailable, or the wing can't be
resolved, or a station yields no geometry (thickness ≤ 0), the corresponding
``y_m`` is simply absent from the maps — the spar service then applies its
documented ``t/c = 0.12`` fallback with a warning. This module NEVER raises for
those cases; it logs and returns what it could compute.

Units: ``SectionGeometry`` works in **mm** (wing-local frame, origin root-LE).
``y_m`` stations are in **metres**, so the span fraction is
``y_span = y_m / half_span_m``.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def build_thickness_maps_for_surface(
    db: Session,
    aeroplane_id: int,
    surface_name: str,
    station_ys_m: list[float],
) -> tuple[dict[float, float], dict[float, float]]:
    """Build ``(thickness_by_y, center_z_by_y)`` for a surface's load stations.

    Resolves ``surface_name`` → the matching wing → a ``WingConfiguration``
    (millimetres), builds a ``SectionGeometry`` once, and queries the
    max-thickness chord location at each ``y_m``.

    Returns two dicts keyed by ``y_m`` (metres):
      * ``thickness_by_y[y_m] = thickness_mm`` — built section thickness.
      * ``center_z_by_y[y_m] = center_z_mm`` — section mid-height (spar ref).

    On any failure (cadquery unavailable, wing not found, conversion error,
    degenerate geometry) the affected stations are omitted and the spar service
    falls back to ``t/c = 0.12``. Never raises.
    """
    if not station_ys_m:
        return {}, {}

    geometry = _build_section_geometry(db, aeroplane_id, surface_name)
    if geometry is None:
        return {}, {}

    half_span_mm = _half_span_mm(geometry)
    if half_span_mm <= 0.0:
        logger.warning(
            "Surface %s has non-positive half-span; spar sizing uses t/c fallback.",
            surface_name,
        )
        return {}, {}

    thickness_by_y: dict[float, float] = {}
    center_z_by_y: dict[float, float] = {}
    for y_m in station_ys_m:
        y_span = abs(float(y_m)) * 1000.0 / half_span_mm
        y_span = min(max(y_span, 0.0), 1.0)
        try:
            point = geometry.at_max_thickness(y_span)
        except Exception as exc:  # pragma: no cover - cadquery boundary (mocked in fast tests)
            logger.warning(
                "Section query failed at y=%.3f m on %s (%s); using t/c fallback there.",
                y_m,
                surface_name,
                exc,
            )
            continue

        thickness_mm = float(point.thickness)
        if thickness_mm <= 0.0:
            logger.warning(
                "Degenerate section (thickness=%.3f mm) at y=%.3f m on %s; t/c fallback there.",
                thickness_mm,
                y_m,
                surface_name,
            )
            continue

        thickness_by_y[float(y_m)] = thickness_mm
        center_z_by_y[float(y_m)] = float(point.center_z)

    return thickness_by_y, center_z_by_y


def _build_section_geometry(db: Session, aeroplane_id: int, surface_name: str):
    """Resolve the wing and build a SectionGeometry, or return None on failure."""
    from app.models.aeroplanemodel import AeroplaneModel
    from app.converters.model_schema_converters import wing_model_to_wing_config
    from cad_designer.airplane.geometry.section_geometry import (
        SectionGeometry,
        SectionGeometryUnavailableError,
    )

    aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.id == aeroplane_id).first()
    if aeroplane is None:
        logger.warning(
            "Aeroplane id=%s not found for spar thickness; using t/c fallback.",
            aeroplane_id,
        )
        return None

    wing = next((w for w in aeroplane.wings if w.name == surface_name), None)
    if wing is None:
        logger.warning(
            "No wing named %r on aeroplane %s; spar sizing uses t/c fallback.",
            surface_name,
            aeroplane_id,
        )
        return None

    try:
        # scale=1000.0 → millimetres (WingConfig convention, SectionGeometry frame)
        wing_config = wing_model_to_wing_config(wing, scale=1000.0)
    except Exception as exc:
        logger.warning(
            "Failed to convert wing %r to WingConfiguration (%s); t/c fallback.",
            surface_name,
            exc,
        )
        return None

    try:
        return SectionGeometry(wing_config)
    except SectionGeometryUnavailableError as exc:
        logger.warning(
            "SectionGeometry unavailable for %r (%s); spar sizing uses t/c fallback.",
            surface_name,
            exc,
        )
        return None
    except Exception as exc:  # pragma: no cover - cadquery boundary (mocked in fast tests)
        logger.warning(
            "SectionGeometry build failed for %r (%s); spar sizing uses t/c fallback.",
            surface_name,
            exc,
        )
        return None


def _half_span_mm(geometry) -> float:
    """Total half-span (mm) of the wing behind a SectionGeometry instance."""
    lengths = getattr(geometry, "_segment_lengths", None)
    if not lengths:
        return 0.0
    return float(sum(lengths))
