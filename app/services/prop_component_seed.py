"""Seed propeller polars as COTS components (gh-1012).

Every propeller in ``propeller_polars`` is mirrored into the generic
``components`` catalog as a ``ComponentModel`` of ``component_type='propeller'``
so propellers become selectable in the component picker / BoM.

Key design points
------------------
* **Keyed on ``model_ref``** — both ``PropellerPolarModel`` and
  ``ComponentModel`` already carry a ``model_ref`` column, so no migration
  is needed. The seed is idempotent: re-runs upsert by ``model_ref``.
* **``mass_g`` is populated from the polar weight** — #1000 (PROP-DATA xlsx)
  is done, so ``propeller_polars.weight_g`` now carries real prop masses in
  grams. On create the component's ``mass_g`` is set from ``weight_g``; on
  reseed a NULL ``mass_g`` is backfilled once the polar gains a weight.
  ``weight_g`` and ``mass_g`` are both grams — no unit conversion.
* **``mass_g`` stays NULL only when the polar has no weight** — there is no
  silent 0-fallback; the BoM marks such nodes as *mass unknown*.
* **User-entered mass is preserved** — a reseed never overwrites a non-null
  ``mass_g`` (neither back to NULL nor with the polar weight).

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


def _mass_from_polar(polar: PropellerPolarModel) -> float | None:
    """Prop mass in grams from the polar weight (#1000). May be ``None``.

    ``weight_g`` and ``mass_g`` are both grams — no unit conversion. Returns
    ``None`` when the polar has no weight; the caller keeps ``mass_g`` NULL
    (no silent 0-fallback) so the BoM can mark the node *mass unknown*.
    """
    return polar.weight_g


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

        mass_g = _mass_from_polar(polar)

        if existing is None:
            comp = ComponentModel(
                name=polar.name,
                component_type=COMPONENT_TYPE,
                manufacturer=polar.manufacturer,
                description=None,
                # Populated from the polar weight (#1000); stays NULL when the
                # polar has no weight — no silent 0-fallback.
                mass_g=mass_g,
                model_ref=polar.model_ref,
                specs=specs,
            )
            db.add(comp)
            result.created += 1
            continue

        # Upsert: refresh catalog metadata from the polar. Backfill a NULL mass
        # from the polar weight, but never clobber a user-entered (non-null)
        # mass — neither back to NULL nor with the polar weight.
        backfill_mass = existing.mass_g is None and mass_g is not None
        changed = (
            existing.name != polar.name
            or existing.manufacturer != polar.manufacturer
            or (existing.specs or {}) != specs
            or backfill_mass
        )
        if changed:
            existing.name = polar.name
            existing.manufacturer = polar.manufacturer
            existing.specs = specs
            if backfill_mass:
                existing.mass_g = mass_g
            result.updated += 1
        else:
            result.skipped += 1

    db.flush()
    logger.info("seed_propeller_components complete: %s", result)
    return result
