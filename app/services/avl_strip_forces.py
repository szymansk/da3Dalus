"""AVL utilities for extracting spanwise strip-force distributions."""

from __future__ import annotations

import logging
import re
import subprocess
import tempfile
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

try:
    import aerosandbox as asb

    HAS_AEROSANDBOX = True
except ImportError:
    HAS_AEROSANDBOX = False

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


if HAS_AEROSANDBOX:
    import numpy as np

    class AVLWithStripForces(asb.AVL):
        """AVL wrapper that additionally captures strip-force distributions.

        Overrides keystroke generation and run() to capture stdout from the
        AVL ``FS`` command, while still producing the standard stability
        output file for the parent's parser.
        """

        def _default_keystroke_file_contents(self) -> List[str]:
            """Return parent keystrokes with an ``fs`` marker appended.

            The ``fs`` entry signals that :meth:`run` should inject the
            strip-forces command into the execution sequence.
            """
            ks = super()._default_keystroke_file_contents()
            ks.append("fs")
            return ks

        def run(self, run_command: str = None) -> dict:
            """Run AVL with strip-force capture.

            Builds the input file via the inherited :meth:`write_avl`, then
            constructs the full command sequence ourselves so that ``fs``
            appears after ``x`` (execute) to capture strip forces from
            stdout.  The stability output is still written via ``st`` so
            that the parent's parser can extract the standard result dict.
            """
            if self.working_directory is not None:
                directory = Path(self.working_directory)
                directory.mkdir(parents=True, exist_ok=True)
                cleanup = None
            else:
                tmp = tempfile.TemporaryDirectory()
                directory = Path(tmp.name)
                cleanup = tmp

            try:
                airplane_file = "airplane.avl"
                output_filename = "output.txt"
                self.write_avl(directory / airplane_file)

                # Build setup keystrokes, removing the "fs" marker we added
                ks = self._default_keystroke_file_contents()
                if run_command is not None:
                    ks.append(run_command)
                ks = [k for k in ks if k != "fs"]

                # Append execution sequence with strip-force capture
                ks += [
                    "x",                     # execute analysis
                    "st",                    # stability output ...
                    output_filename,         # ... to file
                    "o",                     # overwrite if exists
                    "",
                    "fs",                    # strip forces to stdout
                    "",
                    "",
                    "quit",
                ]

                input_text = "\n".join(str(k) for k in ks) + "\n"

                proc = subprocess.Popen(
                    [self.avl_command, airplane_file],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=str(directory),
                )
                stdout_bytes, _ = proc.communicate(
                    input=input_text.encode(), timeout=self.timeout,
                )
                stdout_text = stdout_bytes.decode(errors="replace")

                output_path = directory / output_filename
                if not output_path.exists():
                    raise FileNotFoundError(
                        "AVL didn't produce stability output. "
                        "Check avl_command and input geometry."
                    )
                with open(output_path) as f:
                    raw = f.read()

                result = self.parse_unformatted_data_output(
                    raw, data_identifier=" =", overwrite=False
                )
                result = self._post_process_results(result)
                result["strip_forces"] = parse_strip_forces_output(stdout_text)

                return result
            finally:
                if cleanup is not None:
                    cleanup.cleanup()

        def _post_process_results(self, result: dict) -> dict:
            """Apply the same post-processing as the parent's run() method.

            Mirrors the cleanup / derived-quantity logic from
            ``aerosandbox.AVL.run()`` so callers get an identical result
            dict (plus the extra ``strip_forces`` key).
            """
            op = self.op_point

            # Lowercase canonical keys
            for key_to_lower in ["Alpha", "Beta", "Mach"]:
                if key_to_lower in result:
                    result[key_to_lower.lower()] = result.pop(key_to_lower)

            # Strip "tot" suffix
            for key in list(result.keys()):
                if "tot" in key:
                    result[key.replace("tot", "")] = result.pop(key)

            # Derived quantities
            q = op.dynamic_pressure()
            S = self.airplane.s_ref
            b = self.airplane.b_ref
            c = self.airplane.c_ref

            result["p"] = result.get("pb/2V", 0) * (2 * op.velocity / b) if b else 0
            result["q"] = result.get("qc/2V", 0) * (2 * op.velocity / c) if c else 0
            result["r"] = result.get("rb/2V", 0) * (2 * op.velocity / b) if b else 0

            CL = result.get("CL", 0)
            CY = result.get("CY", 0)
            CD = result.get("CD", 0)
            Cl = result.get("Cl", 0)
            Cm = result.get("Cm", 0)
            Cn = result.get("Cn", 0)

            result["L"] = q * S * CL
            result["Y"] = q * S * CY
            result["D"] = q * S * CD
            result["l_b"] = q * S * b * Cl
            result["m_b"] = q * S * c * Cm
            result["n_b"] = q * S * b * Cn

            try:
                Clb = result.get("Clb", 0)
                Cnr = result.get("Cnr", 0)
                Clr = result.get("Clr", 0)
                Cnb = result.get("Cnb", 0)
                result["Clb Cnr / Clr Cnb"] = Clb * Cnr / (Clr * Cnb)
            except ZeroDivisionError:
                result["Clb Cnr / Clr Cnb"] = np.nan

            F_w = [-result["D"], result["Y"], -result["L"]]
            F_b = op.convert_axes(*F_w, from_axes="wind", to_axes="body")
            F_g = op.convert_axes(*F_b, from_axes="body", to_axes="geometry")

            M_b = [result["l_b"], result["m_b"], result["n_b"]]
            M_g = op.convert_axes(*M_b, from_axes="body", to_axes="geometry")
            M_w = op.convert_axes(*M_b, from_axes="body", to_axes="wind")

            result["F_w"] = F_w
            result["F_b"] = F_b
            result["F_g"] = F_g
            result["M_b"] = M_b
            result["M_g"] = M_g
            result["M_w"] = M_w

            return result
