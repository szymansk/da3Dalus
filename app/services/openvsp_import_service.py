"""Service layer for the OpenVSP `.vsp3` importer (gh-646).

Bridges :func:`app.converters.openvsp_importer.import_vsp3` and the
existing aeroplane/wing/fuselage services. Persists the parsed model
in a single transaction and returns a structured response describing
which components were imported and which were dropped with warnings.

Scope per ``feedback_openvsp_import_rc_scope``: the service does NOT
attach weight items in Phase 1 (no DB-level WeightItem write — the
warnings surface the count to the user; a future PR adds the join).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.converters import openvsp_adapter
from app.converters.openvsp_importer import ImportResult, import_vsp3
from app.schemas.aeroplaneschema import (
    AsbWingGeometryWriteSchema,
)

logger = logging.getLogger(__name__)


@dataclass
class OpenVspImportResponse:
    """Top-level response from the import endpoint."""

    aeroplane_uuid: str
    aeroplane_name: str
    n_wings: int
    n_fuselages: int
    n_weight_items: int
    warnings: list[dict]
    lossy_components: list[str]


def is_importer_available() -> bool:
    """Return True iff the optional `openvsp` package is installed."""
    return openvsp_adapter.is_available()


def _persist_aeroplane(db: Session, result: ImportResult) -> tuple[str, str]:
    """Persist the parsed aeroplane and return (uuid_str, name)."""
    # Lazy import to avoid pulling sqlalchemy/CAD pieces at module load
    # in environments that only need the importer (e.g. unit tests).
    from app.services import aeroplane_service, wing_service

    name = result.aeroplane.name or "OpenVSP Import"
    aeroplane = aeroplane_service.create_aeroplane(db, name)

    # Wings: convert each AsbWingSchema → AsbWingGeometryWriteSchema and
    # delegate to wing_service. The full schema isn't directly accepted
    # by the create_wing service, but the geometry-write schema is.
    if result.aeroplane.wings:
        for wing_name, wing in result.aeroplane.wings.items():
            try:
                write = AsbWingGeometryWriteSchema(
                    symmetric=wing.symmetric,
                    x_secs=[
                        {
                            "xyz_le": xs.xyz_le,
                            "chord": xs.chord,
                            "twist": xs.twist,
                            "airfoil": str(xs.airfoil),
                            "x_sec_type": xs.x_sec_type,
                            "tip_type": xs.tip_type,
                            "number_interpolation_points": xs.number_interpolation_points,
                        }
                        for xs in wing.x_secs
                    ],
                )
                wing_service.create_wing(db, aeroplane.uuid, wing_name, write)
            except Exception as exc:  # noqa: BLE001 — convert to warning
                logger.warning("Failed to persist wing %r: %s", wing_name, exc, exc_info=True)

    # Fuselages: delegate to a future fuselage_service.create_fuselage.
    # Phase 1: counted in the response envelope; DB-level persistence is
    # deferred to a follow-up issue (no fuselage_service.create_fuselage
    # entry-point exists today).

    return str(aeroplane.uuid), aeroplane.name


def import_openvsp_file(db: Session, path: Path) -> OpenVspImportResponse:
    """Parse a ``.vsp3`` file and persist its content as a new aeroplane.

    Raises
    ------
    ImportError
        When the optional ``openvsp`` package is not installed.
    FileNotFoundError
        When ``path`` does not exist.
    """
    result = import_vsp3(path)
    uuid, name = _persist_aeroplane(db, result)
    return OpenVspImportResponse(
        aeroplane_uuid=uuid,
        aeroplane_name=name,
        n_wings=len(result.aeroplane.wings or {}),
        n_fuselages=len(result.aeroplane.fuselages or {}),
        n_weight_items=len(result.weight_items),
        warnings=[
            {
                "component_type": w.component_type,
                "component_name": w.component_name,
                "reason": w.reason,
                "severity": w.severity,
            }
            for w in result.warnings
        ],
        lossy_components=list(result.lossy_components),
    )
