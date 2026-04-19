"""AVL utilities for extracting spanwise strip-force distributions."""

import logging
import re

logger = logging.getLogger(__name__)

# Column names in AVL's FS (strip forces) output table
_STRIP_COLUMNS = [
    "j", "Xle", "Yle", "Zle", "Chord", "Area",
    "c_cl", "ai", "cl_norm", "cl", "cd", "cdv",
    "cm_c/4", "cm_LE", "C.P.x/c",
]


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
        stripped = line.strip()

        # Detect surface header: "Surface # 1     Main Wing"
        m = re.match(r"Surface\s+#\s*(\d+)\s+(.*)", stripped)
        if m:
            current_surface = {
                "surface_number": int(m.group(1)),
                "surface_name": m.group(2).strip(),
                "n_chordwise": 0,
                "n_spanwise": 0,
                "surface_area": 0.0,
                "strips": [],
            }
            surfaces.append(current_surface)
            in_strip_table = False
            continue

        if current_surface is None:
            continue

        # Parse chordwise/spanwise counts
        m = re.match(
            r"#\s*Chordwise\s*=\s*(\d+)\s+#\s*Spanwise\s*=\s*(\d+)",
            stripped,
        )
        if m:
            current_surface["n_chordwise"] = int(m.group(1))
            current_surface["n_spanwise"] = int(m.group(2))
            continue

        # Parse surface area
        m = re.search(r"Surface area\s+Ssurf\s*=\s*([\d.Ee+-]+)", stripped)
        if m:
            current_surface["surface_area"] = float(m.group(1))
            continue

        # Detect strip table header line
        if stripped.startswith("j") and "Xle" in stripped and "cl" in stripped:
            in_strip_table = True
            continue

        # Parse strip data rows (start with an integer index)
        if in_strip_table and stripped and stripped[0].isdigit():
            values = stripped.split()
            if len(values) >= len(_STRIP_COLUMNS):
                row = {}
                for col_name, val_str in zip(_STRIP_COLUMNS, values, strict=False):
                    row[col_name] = int(val_str) if col_name == "j" else float(val_str)
                current_surface["strips"].append(row)
            continue

        # End of strip table (blank line or non-data line after table started)
        if in_strip_table and not stripped:
            in_strip_table = False

    return surfaces
