"""Parse APC PE0 propeller geometry/weight files (gh-1000).

PE0 files (``<designation>-PERF.PE0``) are the geometry/inertia companion to
the PER3 performance polars ingested in #999. Each file carries:

* the canonical designation on line 1 (same format as PER3 — reused parser),
* a per-station blade geometry table (CHORD / PITCH / THICKNESS / SWEEP / …),
* a ``BLADES:`` count,
* total weight (in both lb and **kg**) and moment of inertia (in
  ``SNAIL-IN**2`` and **kg-m²**).

We extract the SI fields (kg, kg-m²) and normalise weight to **grams** at the
boundary so downstream code never sees mixed units. The per-station geometry is
captured verbatim (in inches/degrees) as a list of dicts.

This module has no DB or network dependency — it parses a single file path.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

# Reuse the designation + blade-count parsing already proven for PER3 files.
from scripts.parse_apc_props import derive_blades, parse_header_designation

logger = logging.getLogger(__name__)

KG_TO_G = 1000.0

# Numeric token (handles negatives and decimals).
_NUM = r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?"

_VERSION_RE = re.compile(r"^\s*(v\d{4}-\d{3,4})\s*$")
_BLADES_RE = re.compile(r"BLADES:\s*(\d+)")
_WEIGHT_KG_RE = re.compile(r"TOTAL WEIGHT \(Kg\)\s*=\s*(" + _NUM + r")")
_INERTIA_KGM2_RE = re.compile(r"MOMENT OF INERTIA \(Kg-M\*\*2\)\s*=\s*(" + _NUM + r")")

# A geometry data row: STATION CHORD PITCH PITCH PITCH SWEEP RAKE THICKNESS
# TWIST MAX-THICK CROSS-SECTION ZHIGH CGY CGZ  (14 numeric columns).
_GEOM_ROW_RE = re.compile(r"^\s*(" + _NUM + r")(?:\s+" + _NUM + r"){13}\s*$")

# Subset of geometry columns we name explicitly (rest kept positionally).
_GEOM_COLS = [
    "station_in",
    "chord_in",
    "pitch_quoted_in",
    "pitch_le_te_in",
    "pitch_prather_in",
    "sweep_y_in",
    "rake_z_in",
    "thickness_ratio",
    "twist_deg",
    "max_thick_in",
    "cross_section_in2",
    "zhigh_in",
    "cgy_in",
    "cgz_in",
]


@dataclass
class ParsedPe0:
    """Result of parsing one APC PE0 file."""

    diameter_in: float
    pitch_in: float
    variant: str
    blades: int
    weight_g: float | None
    inertia_kg_m2: float | None
    source_version: str | None
    geometry: list[dict[str, float]] = field(default_factory=list)


def _parse_geometry_row(line: str) -> dict[str, float]:
    values = [float(tok) for tok in line.split()]
    return {name: values[i] for i, name in enumerate(_GEOM_COLS)}


def parse_pe0_file(path: Path) -> ParsedPe0:
    """Parse a single APC ``*.PE0`` file into a :class:`ParsedPe0`.

    Weight is normalised from kg to grams. Inertia stays in kg-m². Diameter,
    pitch and variant come from the line-1 designation; blades from the
    ``BLADES:`` line (cross-checked against the variant token).
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    diameter_in = pitch_in = None
    variant = ""
    blades: int | None = None
    weight_g: float | None = None
    inertia_kg_m2: float | None = None
    source_version: str | None = None
    geometry: list[dict[str, float]] = []

    for idx, line in enumerate(lines):
        if idx == 0:
            desig = parse_header_designation(line)
            if desig:
                diameter_in, pitch_in, variant = desig
            continue

        if source_version is None:
            mver = _VERSION_RE.match(line)
            if mver:
                source_version = mver.group(1)

        if blades is None:
            mb = _BLADES_RE.search(line)
            if mb:
                blades = int(mb.group(1))

        if weight_g is None:
            mw = _WEIGHT_KG_RE.search(line)
            if mw:
                weight_g = float(mw.group(1)) * KG_TO_G

        if inertia_kg_m2 is None:
            mi = _INERTIA_KGM2_RE.search(line)
            if mi:
                inertia_kg_m2 = float(mi.group(1))

        if _GEOM_ROW_RE.match(line):
            geometry.append(_parse_geometry_row(line))

    if diameter_in is None or pitch_in is None:
        raise ValueError(f"PE0 {path.name}: could not parse designation from header")

    # BLADES: line is authoritative; fall back to variant-token derivation.
    if blades is None:
        blades = derive_blades(variant)
        logger.warning("PE0 %s: no BLADES line, derived %d from variant", path.name, blades)

    return ParsedPe0(
        diameter_in=diameter_in,
        pitch_in=pitch_in,
        variant=variant,
        blades=blades,
        weight_g=weight_g,
        inertia_kg_m2=inertia_kg_m2,
        source_version=source_version,
        geometry=geometry,
    )
