"""Seed propeller polars as COTS components (gh-1012).

Every propeller in ``propeller_polars`` is mirrored into the generic
``components`` catalog as a ``ComponentModel`` of ``component_type='propeller'``
so propellers become selectable in the component picker / BoM.

Key design points
------------------
* **Keyed on ``model_ref``** — both ``PropellerPolarModel`` and
  ``ComponentModel`` already carry a ``model_ref`` column, so no migration
  is needed. The seed is idempotent: re-runs upsert by ``model_ref``.
* **``mass_g`` stays NULL** — real masses arrive via #1000 (PROP-DATA xlsx).
  No silent 0-fallback; the BoM marks such nodes as *mass unknown*.
* **User-entered mass is preserved** — a reseed never overwrites a non-null
  ``mass_g`` back to NULL.

The performance bridge (powertrain_performance) resolves a chosen propeller
component back to its polar via the shared ``model_ref``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.component import ComponentModel
from app.models.prop_polar import PropellerPolarModel

logger = logging.getLogger(__name__)

COMPONENT_TYPE = "propeller"


@dataclass
class SeedResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"created={self.created}, updated={self.updated}, "
            f"skipped={self.skipped}, errors={len(self.errors)}"
        )


def _specs_from_polar(polar: PropellerPolarModel) -> dict[str, object]:
    """Build the component specs payload from a polar row."""
    return {
        "diameter_in": polar.diameter_in,
        "pitch_in": polar.pitch_in,
        "blades": polar.blades,
        "variant": polar.variant or "",
    }


def seed_propeller_components(db: Session) -> SeedResult:
    """Upsert one ``propeller`` ComponentModel per propeller polar.

    Idempotent: matches existing components by ``model_ref``. Polars without
    a ``model_ref`` are skipped (cannot be linked back to performance data).
    The caller is responsible for committing the session.
    """
    result = SeedResult()

    polars = db.query(PropellerPolarModel).all()
    for polar in polars:
        if not polar.model_ref:
            msg = f"Polar '{polar.name}' (id={polar.id}) has no model_ref — skipped"
            logger.warning(msg)
            result.skipped += 1
            continue

        specs = _specs_from_polar(polar)
        existing = (
            db.query(ComponentModel)
            .filter_by(component_type=COMPONENT_TYPE, model_ref=polar.model_ref)
            .first()
        )

        if existing is None:
            comp = ComponentModel(
                name=polar.name,
                component_type=COMPONENT_TYPE,
                manufacturer=polar.manufacturer,
                description=None,
                mass_g=None,  # real masses via #1000; no silent 0-fallback
                model_ref=polar.model_ref,
                specs=specs,
            )
            db.add(comp)
            result.created += 1
            continue

        # Upsert: refresh catalog metadata from the polar, but never clobber a
        # user-entered mass back to NULL and never touch a non-null mass.
        changed = (
            existing.name != polar.name
            or existing.manufacturer != polar.manufacturer
            or (existing.specs or {}) != specs
        )
        if changed:
            existing.name = polar.name
            existing.manufacturer = polar.manufacturer
            existing.specs = specs
            result.updated += 1
        else:
            result.skipped += 1

    db.flush()
    logger.info("seed_propeller_components complete: %s", result)
    return result
