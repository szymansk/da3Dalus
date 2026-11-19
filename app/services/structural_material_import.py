"""Structural material records of the COTS snapshot pipeline (gh-1428).

A ``material`` record may carry the PUBLISHED breaking strength in bending, which the kernel reads
for a spar's capacity. It must be a value a handbook or data sheet states, cited with its source
and basis: no safety, resistance or knock-down factor and no estimate (ADR 0028). The snapshot
(``data/cots/structural_materials.json``) is the only way such a value enters the database.
"""

from __future__ import annotations

from typing import Any

# Sanity bound only (a typo guard, not an engineering limit): 1 MPa .. 5000 MPa.
_STRENGTH_MIN_MPA = 1.0
_STRENGTH_MAX_MPA = 5000.0


# The strength and where it comes from. Any other spec needs a sibling ``<key>_source``.
_CITED_KEYS = frozenset(
    {"bending_strength_mpa", "bending_strength_basis", "bending_strength_source"}
)


def _uncited_keys(specs: dict[str, Any]) -> list[str]:
    """The spec keys that say nowhere where they come from."""
    return [
        key
        for key in specs
        if key not in _CITED_KEYS and not key.endswith("_source") and f"{key}_source" not in specs
    ]


def validate_structural_material_record(record: dict[str, Any]) -> str | None:
    """Return an error string if a ``material`` snapshot record is invalid, else ``None``."""
    name = record.get("name", "?")
    if record.get("component_type") != "material":
        return f"'{name}': component_type must be 'material'"
    specs = record.get("specs") or {}
    if uncited := _uncited_keys(specs):
        return f"'{name}': specs {uncited} carry no source; add '<key>_source' or remove them"
    strength = specs.get("bending_strength_mpa")
    if strength is None:
        return None
    if isinstance(strength, bool) or not isinstance(strength, (int, float)):
        return f"'{name}': specs.bending_strength_mpa must be a number"
    if not _STRENGTH_MIN_MPA <= strength <= _STRENGTH_MAX_MPA:
        return (
            f"'{name}': specs.bending_strength_mpa={strength} MPa out of the typo-guard range "
            f"[{_STRENGTH_MIN_MPA}, {_STRENGTH_MAX_MPA}]"
        )
    for key in ("bending_strength_source", "bending_strength_basis"):
        if not specs.get(key):
            return f"'{name}': specs.{key} is required when bending_strength_mpa is set"
    if "allowable_bending_stress_mpa" in specs:
        return (
            f"'{name}': an allowable (safety factor folded in) must not sit next to a published "
            "strength in a snapshot record"
        )
    return None
