"""Enrich PER3 propeller snapshot records with PE0 weight/inertia/geometry (gh-1000).

The PE0 files carry mass / moment-of-inertia / blade geometry that the PER3
polars lack. This module matches a parsed PE0 record to the corresponding
snapshot record by ``(diameter_in, pitch_in, variant)`` and writes the SI
fields into the record's ``specs`` (weight_g, inertia_kg_m2) plus a top-level
``geometry`` list.

Guards (no silent misses):
* **Unit guard** — a parsed weight below ``MIN_PLAUSIBLE_WEIGHT_G`` is treated
  as a likely kg→g conversion error and rejected (counted in
  ``unit_warnings``) rather than written.
* **Unmatched PE0** — a PE0 record with no matching PER3 record is collected
  in ``unmatched_names`` and counted, never dropped silently.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from scripts.parse_apc_pe0 import ParsedPe0

logger = logging.getLogger(__name__)

# A real APC prop weighs at least a few grams; anything below this is almost
# certainly a weight left in kg (e.g. 0.043 instead of 43.3).
MIN_PLAUSIBLE_WEIGHT_G = 1.0


@dataclass
class EnrichResult:
    matched: int = 0
    unmatched_pe0: int = 0
    unit_warnings: int = 0
    unmatched_names: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"matched={self.matched}, unmatched_pe0={self.unmatched_pe0}, "
            f"unit_warnings={self.unit_warnings}"
        )


def _match_key(diameter_in: float, pitch_in: float, variant: str) -> tuple[float, float, str]:
    """Stable match key. Round dims to 3 decimals to absorb float noise."""
    return (round(float(diameter_in), 3), round(float(pitch_in), 3), variant or "")


def _designation(pe0: ParsedPe0) -> str:
    d = f"{pe0.diameter_in:g}x{pe0.pitch_in:g}{pe0.variant}"
    return d


def enrich_records_with_pe0(
    records: list[dict[str, Any]],
    pe0_list: list[ParsedPe0],
) -> EnrichResult:
    """Write PE0 weight/inertia/geometry into matching snapshot records in place.

    Returns an :class:`EnrichResult` summarising matches, unmatched PE0 rows and
    unit warnings.
    """
    result = EnrichResult()

    index: dict[tuple[float, float, str], dict[str, Any]] = {}
    for rec in records:
        specs = rec.get("specs") or {}
        key = _match_key(
            specs.get("diameter_in"),
            specs.get("pitch_in"),
            specs.get("variant", ""),
        )
        index.setdefault(key, rec)

    for pe0 in pe0_list:
        key = _match_key(pe0.diameter_in, pe0.pitch_in, pe0.variant)
        rec = index.get(key)
        if rec is None:
            result.unmatched_pe0 += 1
            result.unmatched_names.append(_designation(pe0))
            logger.warning("PE0 %s has no matching PER3 record", _designation(pe0))
            continue

        specs = rec.setdefault("specs", {})

        if pe0.weight_g is not None:
            if pe0.weight_g < MIN_PLAUSIBLE_WEIGHT_G:
                result.unit_warnings += 1
                logger.warning(
                    "PE0 %s weight %.4g g implausibly small — possible kg→g unit error; skipped",
                    _designation(pe0),
                    pe0.weight_g,
                )
            else:
                specs["weight_g"] = pe0.weight_g

        if pe0.inertia_kg_m2 is not None:
            specs["inertia_kg_m2"] = pe0.inertia_kg_m2

        # PE0 BLADES line is authoritative; align the record's blade count.
        if pe0.blades:
            specs["blades"] = pe0.blades

        if pe0.geometry:
            rec["geometry"] = pe0.geometry

        result.matched += 1

    logger.info("enrich_records_with_pe0 complete: %s", result)
    return result
