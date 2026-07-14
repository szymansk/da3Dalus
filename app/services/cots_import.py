"""COTS Component Import Service — upsert components from a JSON snapshot.

Reads a versioned factual snapshot (e.g. data/cots/dpower.json) and
upserts records into the components table by (manufacturer, name).

Pattern mirrors backfill_airfoil_low_re.py: single transaction, result
report, no network required. The snapshot is the durable reimport source.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models.component import ComponentModel

logger = logging.getLogger(__name__)

# Allowed component_type values.
# gh-1081: 'spar_tube' added for carbon-fibre tube stock; validated separately
# by app.services.carbon_tube_import.validate_spar_tube_record.
# 'material' is the existing seed type (Pine / Carbon Fiber structural defaults).
_VALID_COMPONENT_TYPES = {
    "brushless_motor",
    "esc",
    "battery",
    "propeller",
    "servo",
    "receiver",
    "spar_tube",
    "material",
    # gh-1083: Höllein wood construction stock
    "veneer",
    "strip",
    "triangular_strip",
    "grooved_strip",
}


@dataclass
class ImportResult:
    imported: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"imported={self.imported}, updated={self.updated}, "
            f"skipped={self.skipped}, errors={len(self.errors)}"
        )


def _validate_record(record: dict[str, Any]) -> str | None:
    """Return an error string if the record is invalid, else None."""
    required = ("manufacturer", "name", "component_type")
    for key in required:
        if not record.get(key):
            return f"Missing required field '{key}'"

    ct = record["component_type"]
    if ct not in _VALID_COMPONENT_TYPES:
        return f"Unknown component_type '{ct}'"

    return None


def _build_specs(record: dict[str, Any]) -> dict[str, Any]:
    """Merge snapshot specs + metadata into a single specs dict for the DB.

    source_url and source_version go into specs (not a separate column).
    None values are omitted to keep the JSON compact.
    """
    specs: dict[str, Any] = {}
    if record.get("source_url"):
        specs["source_url"] = record["source_url"]
    if record.get("source_version"):
        specs["source_version"] = record["source_version"]
    for k, v in (record.get("specs") or {}).items():
        if v is not None:
            specs[k] = v
    return specs


def _records_equal(existing: ComponentModel, record: dict[str, Any]) -> bool:
    """Return True if the DB row already matches the snapshot record (skip candidate)."""
    if existing.mass_g != record.get("mass_g"):
        return False
    expected_specs = _build_specs(record)
    if (existing.specs or {}) != expected_specs:
        return False
    if existing.model_ref != record.get("model_ref"):
        return False
    return True


def import_snapshot(
    db: Session,
    records: list[dict[str, Any]],
    *,
    force: bool = False,
) -> ImportResult:
    """Upsert component records from a snapshot list into the DB.

    Parameters
    ----------
    db:
        SQLAlchemy session.  The caller must commit after a successful return;
        on exception the caller should rollback.
    records:
        List of component dicts in the snapshot format (see data/cots/dpower.json).
    force:
        When True, overwrite all fields even if the row appears unchanged.
        Default False: skip rows where existing DB data already matches.

    Returns
    -------
    ImportResult with counts of imported / updated / skipped / errors.
    """
    result = ImportResult()

    for record in records:
        err = _validate_record(record)
        if err:
            msg = f"Record '{record.get('name', '?')}': {err}"
            logger.warning(msg)
            result.errors.append(msg)
            continue

        manufacturer: str = record["manufacturer"]
        name: str = record["name"]
        component_type: str = record["component_type"]

        existing = (
            db.query(ComponentModel)
            .filter(
                ComponentModel.manufacturer == manufacturer,
                ComponentModel.name == name,
            )
            .first()
        )

        specs = _build_specs(record)

        if existing is None:
            db.add(
                ComponentModel(
                    manufacturer=manufacturer,
                    name=name,
                    component_type=component_type,
                    mass_g=record.get("mass_g"),
                    bbox_x_mm=record.get("bbox_x_mm"),
                    bbox_y_mm=record.get("bbox_y_mm"),
                    bbox_z_mm=record.get("bbox_z_mm"),
                    model_ref=record.get("model_ref"),
                    specs=specs,
                )
            )
            logger.info("Import: %s / %s", manufacturer, name)
            result.imported += 1
        else:
            if not force and _records_equal(existing, record):
                result.skipped += 1
                continue

            existing.component_type = component_type
            existing.mass_g = record.get("mass_g")
            existing.bbox_x_mm = record.get("bbox_x_mm")
            existing.bbox_y_mm = record.get("bbox_y_mm")
            existing.bbox_z_mm = record.get("bbox_z_mm")
            existing.model_ref = record.get("model_ref")
            existing.specs = specs
            logger.info("Update: %s / %s", manufacturer, name)
            result.updated += 1

    return result
