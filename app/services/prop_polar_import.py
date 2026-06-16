"""Propeller polar import service (gh-995).

Reads a versioned factual snapshot (data/cots/apc_props.json) and upserts
propeller polar records into the DB by (manufacturer, name).

Pattern mirrors cots_import.py: single transaction, result report,
no network required. The snapshot is the durable reimport source.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models.prop_polar import PropellerPolarModel, PropellerPolarSampleModel

logger = logging.getLogger(__name__)


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


def _validate_prop_record(record: dict[str, Any]) -> str | None:
    """Return an error string if the record is invalid, else None."""
    for key in ("manufacturer", "name"):
        if not record.get(key):
            return f"Missing required field '{key}'"

    ct = record.get("component_type")
    if ct != "propeller":
        return f"Expected component_type='propeller', got '{ct}'"

    return None


def _records_equal(existing: PropellerPolarModel, record: dict[str, Any]) -> bool:
    """True if the DB row already matches the snapshot (skip candidate).

    We compare source_version as the proxy for data freshness.
    If source_version differs we always re-import. Exact sample equality
    comparison is too expensive to run on every row.

    Limitation: if APC corrects polar data WITHOUT bumping source_version,
    the change is silently skipped — run the importer with ``force=True`` to
    re-import regardless.
    """
    if existing.source_version != record.get("source_version"):
        return False
    if existing.source_url != record.get("source_url"):
        return False
    return True


def _upsert_samples(
    db: Session,
    prop: PropellerPolarModel,
    polars: list[dict[str, Any]],
) -> None:
    """Replace all samples for a propeller with the snapshot's data."""
    # Delete existing samples (cascade would work too, but explicit is clearer)
    db.query(PropellerPolarSampleModel).filter_by(propeller_id=prop.id).delete(
        synchronize_session="fetch"
    )

    for polar in polars:
        rpm = int(polar["rpm"])
        for s in polar.get("samples", []):
            db.add(
                PropellerPolarSampleModel(
                    propeller_id=prop.id,
                    rpm=rpm,
                    J=s["J"],
                    Ct=s["Ct"],
                    Cp=s["Cp"],
                    Pe=s.get("Pe"),
                    PWR_W=s.get("PWR_W"),
                    Torque_Nm=s.get("Torque_Nm"),
                    Thrust_N=s.get("Thrust_N"),
                )
            )


def import_prop_polars(
    db: Session,
    records: list[dict[str, Any]],
    *,
    force: bool = False,
) -> ImportResult:
    """Upsert propeller polar records from a snapshot list into the DB.

    Parameters
    ----------
    db:
        SQLAlchemy session. The caller must commit after a successful return.
    records:
        List of propeller dicts in the snapshot format (see data/cots/apc_props.json).
    force:
        When True, overwrite all fields and replace samples even if the version
        matches. Default False: skip rows where source_version already matches.

    Returns
    -------
    ImportResult with counts of imported / updated / skipped / errors.
    """
    result = ImportResult()

    for record in records:
        err = _validate_prop_record(record)
        if err:
            msg = f"Record '{record.get('name', '?')}': {err}"
            logger.warning(msg)
            result.errors.append(msg)
            continue

        manufacturer: str = record["manufacturer"]
        name: str = record["name"]
        specs: dict[str, Any] = record.get("specs") or {}
        polars: list[dict[str, Any]] = record.get("polars") or []

        existing = (
            db.query(PropellerPolarModel).filter_by(manufacturer=manufacturer, name=name).first()
        )

        if existing is None:
            prop = PropellerPolarModel(
                manufacturer=manufacturer,
                name=name,
                model_ref=record.get("model_ref"),
                source_url=record.get("source_url"),
                source_version=record.get("source_version"),
                diameter_in=specs.get("diameter_in"),
                pitch_in=specs.get("pitch_in"),
                blades=specs.get("blades", 2),
            )
            db.add(prop)
            db.flush()  # get prop.id before inserting samples
            _upsert_samples(db, prop, polars)
            logger.info("Import: %s / %s (%d RPM blocks)", manufacturer, name, len(polars))
            result.imported += 1

        else:
            if not force and _records_equal(existing, record):
                result.skipped += 1
                continue

            existing.model_ref = record.get("model_ref")
            existing.source_url = record.get("source_url")
            existing.source_version = record.get("source_version")
            existing.diameter_in = specs.get("diameter_in")
            existing.pitch_in = specs.get("pitch_in")
            existing.blades = specs.get("blades", 2)
            db.flush()
            _upsert_samples(db, existing, polars)
            logger.info("Update: %s / %s (%d RPM blocks)", manufacturer, name, len(polars))
            result.updated += 1

    return result
