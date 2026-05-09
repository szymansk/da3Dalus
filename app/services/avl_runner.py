"""Standalone AVL runner — replaces asb.AVL for all AVL operations.

Owns the full lifecycle from geometry file to parsed results.
Does not inherit from Aerosandbox. Accepts an Aerosandbox Airplane and
OperatingPoint for geometry/flight condition data, but handles all AVL
interaction independently.
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

if TYPE_CHECKING:
    import aerosandbox as asb

    from app.schemas.aeroanalysisschema import TrimConstraint

logger = logging.getLogger(__name__)


def parse_stability_output(raw: str) -> dict[str, float]:
    """Parse AVL stability output file into a dict of key-value pairs.

    Reimplements the parsing logic from ``asb.AVL.parse_unformatted_data_output()``.
    Scans for ``' = '`` identifiers, extracts the key (word before) and value
    (word after). First occurrence wins if duplicate keys exist.
    """
    items: dict[str, float] = {}
    data_identifier = " = "
    s = raw
    index = s.find(data_identifier)

    while index != -1:
        # Read key backwards from left of identifier
        key = ""
        i = index - 1
        while i >= 0 and s[i] == " ":
            i -= 1
        while i >= 0 and s[i] not in (" ", "\n"):
            key = s[i] + key
            i -= 1

        # Read value forwards from right of identifier
        value_str = ""
        i = index + len(data_identifier)
        while i < len(s) and s[i] == " ":
            i += 1
        while i < len(s) and s[i] not in (" ", "\n"):
            value_str += s[i]
            i += 1

        try:
            value = float(value_str)
        except (ValueError, TypeError):
            value = float("nan")

        if key not in items:  # First occurrence wins
            items[key] = value

        s = s[index + len(data_identifier) :]
        index = s.find(data_identifier)

    return items


def _resolve_avl_path() -> Path:
    """Find the AVL binary, falling back to the main worktree if needed."""
    local = _PROJECT_ROOT / "exports" / "avl"
    if local.exists():
        return local

    # In a git worktree the binary lives in the main worktree's exports/
    try:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=_PROJECT_ROOT,
            timeout=5,
        )
        for line in result.stdout.splitlines():
            if line.startswith("worktree "):
                main_avl = Path(line.split(" ", 1)[1]) / "exports" / "avl"
                if main_avl.exists():
                    return main_avl
    except (subprocess.SubprocessError, OSError):
        pass

    # Return the local path anyway — will fail at runtime with a clear error
    return local


class AVLRunner:
    """Standalone AVL runner — owns the full lifecycle from geometry to results.

    Replaces ``asb.AVL`` for all AVL operations. Does not inherit from
    Aerosandbox. Accepts an Aerosandbox Airplane and OperatingPoint for
    geometry/flight condition data, but handles all AVL interaction
    independently.
    """

    DEFAULT_AVL_COMMAND = str(_resolve_avl_path())

    def __init__(
        self,
        airplane: asb.Airplane,
        op_point: asb.OperatingPoint,
        xyz_ref: list[float],
        avl_command: str | None = None,
        timeout: float = 30,
        working_directory: str | None = None,
    ):
        self.airplane = airplane
        self.op_point = op_point
        self.xyz_ref = xyz_ref
        self.avl_command = avl_command or self.DEFAULT_AVL_COMMAND
        self.timeout = timeout
        self.working_directory = working_directory

    def _build_keystrokes(
        self,
        output_filename: str,
        control_overrides: dict[str, float] | None = None,
        include_strip_forces: bool = False,
        extra_keystrokes: list[str] | None = None,
    ) -> list[str]:
        """Build the complete AVL keystroke sequence.

        Sequence:
        1. OPER -- enter operating mode
        2. Mass parameters (Mach, velocity, density, gravity) via ``m`` submenu
        3. Operating point (alpha, beta, non-dimensional roll/pitch/yaw rates)
        4. Control deflection commands (d1 d1 <value>, d2 d2 <value>, ...)
        5. Extra keystrokes (for trim constraints)
        6. x -- execute analysis
        7. st <filename> o -- write stability output
        8. Optionally: fs -- print strip forces to stdout
        9. quit
        """
        from app.services.avl_strip_forces import build_control_deflection_commands

        op = self.op_point
        b = self.airplane.b_ref
        c = self.airplane.c_ref
        v = op.velocity

        ks: list[str] = ["OPER"]
        ks += [
            "m",
            f"mn {op.mach()}",
            f"v {v}",
            f"d {op.atmosphere.density()}",
            "g 9.81",
            "",
        ]
        pb2v = op.p * b / (2 * v) if v and b else 0
        qc2v = op.q * c / (2 * v) if v and c else 0
        rb2v = op.r * b / (2 * v) if v and b else 0
        if not v and any(getattr(op, attr, 0) for attr in ("p", "q", "r")):
            logger.warning("velocity=0 with nonzero angular rates; rates zeroed for AVL")
        ks += [
            f"a a {op.alpha}",
            f"b b {op.beta}",
            f"r r {pb2v}",
            f"p p {qc2v}",
            f"y y {rb2v}",
        ]
        ks += build_control_deflection_commands(self.airplane, control_overrides)
        if extra_keystrokes:
            ks += extra_keystrokes
        ks += [
            "x",  # execute analysis
            "st",  # stability output...
            output_filename,  # ...to file
            "o",  # overwrite if exists
            "",  # blank to clear prompt
        ]
        if include_strip_forces:
            ks += [
                "fs",  # strip forces to stdout
                "",  # blank to clear prompt
            ]
        ks += ["", "quit"]
        return ks

    def _post_process_results(self, result: dict) -> dict:
        """Apply same post-processing as the old ``asb.AVL.run()``.

        - Lowercase canonical keys (Alpha, Beta, Mach)
        - Strip 'tot' suffix from coefficient keys
        - Compute dimensional forces/moments from coefficients
        - Compute body/geometry/wind axis force/moment vectors
        """
        op = self.op_point

        # Lowercase canonical keys
        for key_to_lower in ["Alpha", "Beta", "Mach"]:
            if key_to_lower in result:
                result[key_to_lower.lower()] = result.pop(key_to_lower)

        # Strip "tot" suffix (e.g. CLtot → CL, Cl'tot → Cl')
        for key in list(result.keys()):
            if key.endswith("tot"):
                result[key.removesuffix("tot")] = result.pop(key)

        # Derived quantities
        q = op.dynamic_pressure()
        S = self.airplane.s_ref  # noqa: N806 — standard aero variable
        b = self.airplane.b_ref
        c = self.airplane.c_ref

        result["p"] = result.get("pb/2V", 0) * (2 * op.velocity / b) if b else 0
        result["q"] = result.get("qc/2V", 0) * (2 * op.velocity / c) if c else 0
        result["r"] = result.get("rb/2V", 0) * (2 * op.velocity / b) if b else 0

        CL = result.get("CL", 0)  # noqa: N806 — standard aero coefficient
        CY = result.get("CY", 0)  # noqa: N806 — standard aero coefficient
        CD = result.get("CD", 0)  # noqa: N806 — standard aero coefficient
        Cl = result.get("Cl", 0)  # noqa: N806 — standard aero coefficient
        Cm = result.get("Cm", 0)  # noqa: N806 — standard aero coefficient
        Cn = result.get("Cn", 0)  # noqa: N806 — standard aero coefficient

        result["L"] = q * S * CL
        result["Y"] = q * S * CY
        result["D"] = q * S * CD
        result["l_b"] = q * S * b * Cl
        result["m_b"] = q * S * c * Cm
        result["n_b"] = q * S * b * Cn

        try:
            Clb = result.get("Clb", 0)  # noqa: N806 — standard aero coefficient
            Cnr = result.get("Cnr", 0)  # noqa: N806 — standard aero coefficient
            Clr = result.get("Clr", 0)  # noqa: N806 — standard aero coefficient
            Cnb = result.get("Cnb", 0)  # noqa: N806 — standard aero coefficient
            result["Clb Cnr / Clr Cnb"] = Clb * Cnr / (Clr * Cnb)
        except ZeroDivisionError:
            result["Clb Cnr / Clr Cnb"] = float("nan")

        F_w = [-result["D"], result["Y"], -result["L"]]  # noqa: N806 — force in wind axes
        F_b = op.convert_axes(  # noqa: N806 — force in body axes
            *F_w, from_axes="wind", to_axes="body"
        )
        F_g = op.convert_axes(  # noqa: N806 — force in geometry axes
            *F_b, from_axes="body", to_axes="geometry"
        )

        M_b = [  # noqa: N806 — moment in body axes
            result["l_b"],
            result["m_b"],
            result["n_b"],
        ]
        M_g = op.convert_axes(  # noqa: N806 — moment in geometry axes
            *M_b, from_axes="body", to_axes="geometry"
        )
        M_w = op.convert_axes(  # noqa: N806 — moment in wind axes
            *M_b, from_axes="body", to_axes="wind"
        )

        result["F_w"] = F_w
        result["F_b"] = F_b
        result["F_g"] = F_g
        result["M_b"] = M_b
        result["M_g"] = M_g
        result["M_w"] = M_w

        return result

    def run_trim(
        self,
        avl_file_content: str,
        trim_constraints: list[TrimConstraint],
        control_overrides: dict[str, float] | None = None,
    ) -> dict:
        """Run AVL with indirect constraints for trim analysis.

        Builds indirect constraint keystrokes from trim_constraints,
        injects them as extra_keystrokes, and runs AVL.
        The result includes the achieved deflections/state from AVL's convergence.
        """
        from app.services.avl_strip_forces import build_indirect_constraint_commands

        extra_ks = build_indirect_constraint_commands(self.airplane, trim_constraints)
        return self.run(
            avl_file_content=avl_file_content,
            control_overrides=control_overrides,
            extra_keystrokes=extra_ks,
        )

    def run(
        self,
        avl_file_content: str,
        control_overrides: dict[str, float] | None = None,
        include_strip_forces: bool = False,
        extra_keystrokes: list[str] | None = None,
    ) -> dict:
        """Run AVL analysis.

        Args:
            avl_file_content: Complete AVL geometry file content as string.
            control_overrides: Optional per-surface deflection overrides.
            include_strip_forces: If True, also capture strip force distributions.
            extra_keystrokes: Optional additional keystrokes (for future trim support).

        Returns:
            Dict with parsed stability results and optionally ``strip_forces`` key.

        Raises:
            FileNotFoundError: If AVL doesn't produce stability output.
            RuntimeError: If AVL times out.
        """
        output_filename = "output.txt"
        airplane_file = "airplane.avl"

        if self.working_directory is not None:
            directory = Path(self.working_directory)
            directory.mkdir(parents=True, exist_ok=True)
            cleanup = None
        else:
            tmp = tempfile.TemporaryDirectory()
            directory = Path(tmp.name)
            cleanup = tmp

        try:
            (directory / airplane_file).write_text(avl_file_content)

            keystrokes = self._build_keystrokes(
                output_filename,
                control_overrides=control_overrides,
                include_strip_forces=include_strip_forces,
                extra_keystrokes=extra_keystrokes,
            )
            input_text = "\n".join(str(k) for k in keystrokes) + "\n"

            proc = subprocess.Popen(
                [self.avl_command, airplane_file],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(directory),
            )
            try:
                stdout_bytes, _ = proc.communicate(
                    input=input_text.encode(),
                    timeout=self.timeout,
                )
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()
                raise RuntimeError(
                    f"AVL timed out after {self.timeout}s. Try increasing the timeout parameter."
                )

            if proc.returncode != 0:
                logger.warning("AVL exited with code %d", proc.returncode)

            output_path = directory / output_filename
            if not output_path.exists():
                stderr_text = stdout_bytes.decode(errors="replace") if stdout_bytes else ""
                raise FileNotFoundError(
                    f"AVL didn't produce stability output. Check avl_command and input geometry. "
                    f"stderr/stdout hint: {stderr_text[:500]}"
                )
            raw = output_path.read_text()

            result = parse_stability_output(raw)
            result = self._post_process_results(result)

            if include_strip_forces:
                from app.services.avl_strip_forces import parse_strip_forces_output

                stdout_text = stdout_bytes.decode(errors="replace")
                result["strip_forces"] = parse_strip_forces_output(stdout_text)

            return result
        finally:
            if cleanup is not None:
                cleanup.cleanup()
