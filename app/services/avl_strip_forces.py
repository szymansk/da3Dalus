"""AVL utilities for extracting spanwise strip-force distributions."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Column names in AVL's FS (strip forces) output table
_STRIP_COLUMNS = [
    "j",
    "Xle",
    "Yle",
    "Zle",
    "Chord",
    "Area",
    "c_cl",
    "ai",
    "cl_norm",
    "cl",
    "cd",
    "cdv",
    "cm_c/4",
    "cm_LE",
    "C.P.x/c",
]


def _parse_surface_header(stripped: str) -> dict | None:
    """Detect and parse a "Surface # N Name" header line.

    Returns a new surface dict if matched, or ``None``.
    """
    m = re.match(r"Surface\s+#\s*(\d+)\s+(.*)", stripped)
    if not m:
        return None
    return {
        "surface_number": int(m.group(1)),
        "surface_name": m.group(2).strip(),
        "n_chordwise": 0,
        "n_spanwise": 0,
        "surface_area": 0.0,
        "strips": [],
    }


def _parse_strip_row(values: list[str], columns: list[str]) -> dict | None:
    """Convert raw split values to a strip row dict.

    Returns a dict keyed by *columns* or ``None`` if *values* has
    fewer elements than *columns*.
    """
    if len(values) < len(columns):
        return None
    return {
        col: int(val) if col == "j" else float(val)
        for col, val in zip(columns, values, strict=False)
    }


def _try_parse_metadata(stripped: str, surface: dict) -> bool:
    """Try to parse chordwise/spanwise/area metadata from *stripped*.

    Mutates *surface* in place and returns ``True`` if any field
    matched, ``False`` otherwise.
    """
    m = re.match(
        r"#\s*Chordwise\s*=\s*(\d+)\s+#\s*Spanwise\s*=\s*(\d+)",
        stripped,
    )
    if m:
        surface["n_chordwise"] = int(m.group(1))
        surface["n_spanwise"] = int(m.group(2))
        return True

    m = re.search(r"Surface area\s+Ssurf\s*=\s*([\d.Ee+-]+)", stripped)
    if m:
        surface["surface_area"] = float(m.group(1))
        return True

    return False


def _is_strip_table_header(stripped: str) -> bool:
    """Return True if the line is a strip-table column header."""
    return stripped.startswith("j") and "Xle" in stripped and "cl" in stripped


def _process_strip_line(
    stripped: str, current_surface: dict | None, in_strip_table: bool, surfaces: list[dict]
) -> tuple[dict | None, bool]:
    """Process a single line of AVL strip-forces output.

    Returns updated (current_surface, in_strip_table).
    """
    header = _parse_surface_header(stripped)
    if header is not None:
        surfaces.append(header)
        return header, False

    if current_surface is None:
        return None, in_strip_table

    if _try_parse_metadata(stripped, current_surface):
        return current_surface, in_strip_table

    if _is_strip_table_header(stripped):
        return current_surface, True

    if in_strip_table and stripped and stripped[0].isdigit():
        row = _parse_strip_row(stripped.split(), _STRIP_COLUMNS)
        if row is not None:
            current_surface["strips"].append(row)
        return current_surface, in_strip_table

    if in_strip_table and not stripped:
        return current_surface, False

    return current_surface, in_strip_table


def parse_strip_forces_output(stdout: str) -> list[dict]:
    """Parse AVL's ``FS`` (strip forces) stdout output into structured data.

    Returns a list of dicts, one per surface, each containing:
    - ``surface_name``: str
    - ``surface_number``: int
    - ``n_chordwise``: int
    - ``n_spanwise``: int
    - ``surface_area``: float
    - ``strips``: list of dicts with keys from ``_STRIP_COLUMNS``
    """
    surfaces: list[dict] = []
    current_surface: dict | None = None
    in_strip_table = False

    for line in stdout.splitlines():
        current_surface, in_strip_table = _process_strip_line(
            line.strip(), current_surface, in_strip_table, surfaces
        )

    return surfaces


def build_control_deflection_commands(
    airplane,
    overrides: dict[str, float] | None = None,
) -> list[str]:
    """Build AVL keystroke commands to set correct control surface deflections.

    Aerosandbox hardcodes ``d1 d1 1`` — this produces correct overrides.
    When *overrides* is provided, matching control surface names use the
    override value instead of the geometry default.
    """
    seen: dict[str, float] = {}
    for wing in airplane.wings:
        for xsec in wing.xsecs:
            for cs in xsec.control_surfaces:
                if cs.name not in seen:
                    seen[cs.name] = float(cs.deflection)
    if overrides:
        for name, defl in overrides.items():
            if name in seen:
                seen[name] = float(defl)
    return [f"d{i} d{i} {defl}" for i, defl in enumerate(seen.values(), 1)]
