# AVL Strip Forces Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose spanwise strip-force distributions from AVL via a REST endpoint.

**Architecture:** Subclass `asb.AVL` to capture strip-force stdout output, parse the tabular data, and serve it through a new endpoint. The `FS` command in AVL's OPER menu prints strip forces to stdout (not to a file), so we capture the full subprocess stdout and extract the strip-force section.

**Tech Stack:** Python 3.11, FastAPI, Aerosandbox, pytest

**Design spec:** `docs/superpowers/specs/2026-04-19-avl-strip-forces-design.md`

**AVL binary:** `exports/avl` (must be passed as `avl_command` parameter)

---

### Task 1: Strip-force parser — unit test + implementation

**Files:**
- Create: `app/services/avl_strip_forces.py`
- Create: `app/tests/test_avl_strip_forces.py`

The AVL `FS` command prints to stdout with this format per surface:

```
  Surface # 1     Main Wing
     # Chordwise = 12   # Spanwise = 12     First strip =  1
     Surface area Ssurf =    0.125000     Ave. chord Cave =    0.250000
 ...
 Strip Forces referred to Strip Area, Chord
    j     Xle      Yle      Zle      Chord    Area     c_cl     ai     cl_norm    cl       cd       cdv    cm_c/4     cm_LE   C.P.x/c
     1   0.0001   0.0021   0.0000   0.2996   0.0026   0.1064   0.0563   0.3555   0.3555   0.0117   0.0000   0.0128  -0.0759    0.214
     2   0.0008   0.0190   0.0000   0.2962   0.0074   0.1063   0.0550   0.3592   0.3592   0.0103   0.0000   0.0130  -0.0766    0.214
```

- [ ] **Step 1: Write failing test for parser**

```python
# app/tests/test_avl_strip_forces.py
import pytest
from app.services.avl_strip_forces import parse_strip_forces_output

SAMPLE_FS_OUTPUT = """
 Surface and Strip Forces by surface

  Sref = 0.25000       Cref = 0.25333       Bref =  1.0000
  Xref =  0.0000       Yref =  0.0000       Zref =  0.0000

  Surface # 1     Main Wing
     # Chordwise = 12   # Spanwise = 12     First strip =  1
     Surface area Ssurf =    0.125000     Ave. chord Cave =    0.250000

 Forces referred to Sref, Cref, Bref about Xref, Yref, Zref
 Standard axis orientation,  X fwd, Z down
     CLsurf  =   0.16769     Clsurf  =  -0.03573
     CYsurf  =  -0.00190     Cmsurf  =  -0.04143
     CDsurf  =   0.00450     Cnsurf  =  -0.00157
     CDisurf =   0.00450     CDvsurf =   0.00000

 Forces referred to Ssurf, Cave
     CLsurf  =   0.33539     CDsurf  =   0.00900

 Strip Forces referred to Strip Area, Chord
    j     Xle      Yle      Zle      Chord    Area     c_cl     ai     cl_norm    cl       cd       cdv    cm_c/4     cm_LE   C.P.x/c
     1   0.0001   0.0021   0.0000   0.2996   0.0026   0.1064   0.0563   0.3555   0.3555   0.0117   0.0000   0.0128  -0.0759    0.214
     2   0.0008   0.0190   0.0000   0.2962   0.0074   0.1063   0.0550   0.3592   0.3592   0.0103   0.0000   0.0130  -0.0766    0.214
     3   0.0021   0.0517   0.0000   0.2897   0.0115   0.1056   0.0535   0.3649   0.3649   0.0098   0.0000   0.0131  -0.0779    0.214

  Surface # 2     Main Wing (YDUP)
     # Chordwise = 12   # Spanwise = 12     First strip = 13
     Surface area Ssurf =    0.125000     Ave. chord Cave =    0.250000

 Forces referred to Sref, Cref, Bref about Xref, Yref, Zref
 Standard axis orientation,  X fwd, Z down
     CLsurf  =   0.16769     Clsurf  =   0.03573
     CYsurf  =   0.00190     Cmsurf  =  -0.04143
     CDsurf  =   0.00450     Cnsurf  =   0.00157
     CDisurf =   0.00450     CDvsurf =   0.00000

 Forces referred to Ssurf, Cave
     CLsurf  =   0.33539     CDsurf  =   0.00900

 Strip Forces referred to Strip Area, Chord
    j     Xle      Yle      Zle      Chord    Area     c_cl     ai     cl_norm    cl       cd       cdv    cm_c/4     cm_LE   C.P.x/c
    13   0.0001  -0.0021   0.0000   0.2996   0.0026   0.1064   0.0563   0.3555   0.3555   0.0117   0.0000   0.0128   0.0759    0.214
    14   0.0008  -0.0190   0.0000   0.2962   0.0074   0.1063   0.0550   0.3592   0.3592   0.0103   0.0000   0.0130   0.0766    0.214
    15   0.0021  -0.0517   0.0000   0.2897   0.0115   0.1056   0.0535   0.3649   0.3649   0.0098   0.0000   0.0131   0.0779    0.214
"""


class TestParseStripForcesOutput:
    def test_parses_two_surfaces(self):
        result = parse_strip_forces_output(SAMPLE_FS_OUTPUT)
        assert len(result) == 2
        assert result[0]["surface_name"] == "Main Wing"
        assert result[1]["surface_name"] == "Main Wing (YDUP)"

    def test_parses_strip_data(self):
        result = parse_strip_forces_output(SAMPLE_FS_OUTPUT)
        strips = result[0]["strips"]
        assert len(strips) == 3
        assert strips[0]["j"] == 1
        assert strips[0]["Yle"] == pytest.approx(0.0021)
        assert strips[0]["Chord"] == pytest.approx(0.2996)
        assert strips[0]["cl"] == pytest.approx(0.3555)
        assert strips[0]["cd"] == pytest.approx(0.0117)
        assert strips[0]["cm_c/4"] == pytest.approx(0.0128)
        assert strips[0]["C.P.x/c"] == pytest.approx(0.214)

    def test_parses_surface_metadata(self):
        result = parse_strip_forces_output(SAMPLE_FS_OUTPUT)
        assert result[0]["n_chordwise"] == 12
        assert result[0]["n_spanwise"] == 12
        assert result[0]["surface_area"] == pytest.approx(0.125)

    def test_empty_output(self):
        result = parse_strip_forces_output("")
        assert result == []

    def test_output_without_strip_section(self):
        result = parse_strip_forces_output("Some random AVL output\nwithout strip data")
        assert result == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest app/tests/test_avl_strip_forces.py -v`
Expected: FAIL — `ImportError: cannot import name 'parse_strip_forces_output'`

- [ ] **Step 3: Implement parser**

```python
# app/services/avl_strip_forces.py
"""AVL subclass and utilities for extracting spanwise strip-force distributions."""

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
                for col_name, val_str in zip(_STRIP_COLUMNS, values):
                    row[col_name] = int(val_str) if col_name == "j" else float(val_str)
                current_surface["strips"].append(row)
            continue

        # End of strip table (blank line or non-data line after table started)
        if in_strip_table and not stripped:
            in_strip_table = False

    return surfaces
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest app/tests/test_avl_strip_forces.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add app/services/avl_strip_forces.py app/tests/test_avl_strip_forces.py
git commit -m "feat(#140): strip-force parser with unit tests"
```

---

### Task 2: AVLWithStripForces subclass

**Files:**
- Modify: `app/services/avl_strip_forces.py`
- Modify: `app/tests/test_avl_strip_forces.py`

- [ ] **Step 1: Write failing test for keystroke extension**

```python
# append to app/tests/test_avl_strip_forces.py

class TestAVLWithStripForcesKeystrokes:
    def test_keystrokes_contain_fs_command(self):
        """The extended keystroke sequence must include the FS command."""
        from app.services.avl_strip_forces import AVLWithStripForces
        import aerosandbox as asb

        airplane = asb.Airplane(
            name="test",
            wings=[asb.Wing(name="W", symmetric=True, xsecs=[
                asb.WingXSec(xyz_le=[0, 0, 0], chord=0.3, airfoil=asb.Airfoil("naca0012")),
                asb.WingXSec(xyz_le=[0, 0.5, 0], chord=0.2, airfoil=asb.Airfoil("naca0012")),
            ])],
        )
        op = asb.OperatingPoint(velocity=20, alpha=5)
        avl = AVLWithStripForces(airplane=airplane, op_point=op)
        ks = avl._default_keystroke_file_contents()
        assert "fs" in ks, "FS command must be in keystroke sequence"

    def test_keystrokes_preserve_parent_commands(self):
        """All parent keystroke commands must still be present."""
        from app.services.avl_strip_forces import AVLWithStripForces
        import aerosandbox as asb

        airplane = asb.Airplane(
            name="test",
            wings=[asb.Wing(name="W", symmetric=True, xsecs=[
                asb.WingXSec(xyz_le=[0, 0, 0], chord=0.3, airfoil=asb.Airfoil("naca0012")),
                asb.WingXSec(xyz_le=[0, 0.5, 0], chord=0.2, airfoil=asb.Airfoil("naca0012")),
            ])],
        )
        op = asb.OperatingPoint(velocity=20, alpha=5)
        avl = AVLWithStripForces(airplane=airplane, op_point=op)
        ks = avl._default_keystroke_file_contents()
        # Parent keystrokes that must be preserved
        assert "plop" in ks
        assert "oper" in ks
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest app/tests/test_avl_strip_forces.py::TestAVLWithStripForcesKeystrokes -v`
Expected: FAIL — `ImportError: cannot import name 'AVLWithStripForces'`

- [ ] **Step 3: Implement AVLWithStripForces subclass**

Append to `app/services/avl_strip_forces.py`:

```python
import subprocess
import tempfile
from pathlib import Path

try:
    import aerosandbox as asb
    HAS_AEROSANDBOX = True
except ImportError:
    HAS_AEROSANDBOX = False

if HAS_AEROSANDBOX:

    class AVLWithStripForces(asb.AVL):
        """AVL wrapper that additionally captures strip-force distributions.

        Overrides the keystroke sequence to include the ``FS`` command, which
        prints strip forces to stdout.  The ``run()`` method captures stdout,
        extracts the strip-force section, and adds a ``strip_forces`` key to
        the returned result dictionary.
        """

        def _default_keystroke_file_contents(self) -> list:
            """Extend parent keystrokes — no change needed.

            The ``FS`` command is injected in ``run()`` via the ``run_command``
            parameter, not here, because the parent's ``run()`` appends its own
            execute + output commands *after* these keystrokes.
            """
            return super()._default_keystroke_file_contents()

        def run(self) -> dict:
            """Run AVL with strip-force capture.

            Strategy: we let the parent build the input file and provide its
            keystrokes. We then construct the full command sequence ourselves,
            adding ``fs`` after ``x`` (execute) to capture strip forces from
            stdout. We still write the stability output via ``st`` so the
            parent's parser can extract the standard result dict.
            """
            import pathlib

            # Determine working directory (mirrors parent logic)
            if self.working_directory is not None:
                directory = pathlib.Path(self.working_directory)
                directory.mkdir(parents=True, exist_ok=True)
                cleanup = None
            else:
                tmp = tempfile.TemporaryDirectory()
                directory = pathlib.Path(tmp.name)
                cleanup = tmp

            try:
                airplane_file = str(directory / "airplane.avl")
                output_filename = "output.txt"
                self.write_avl(airplane_file)

                ks = self._default_keystroke_file_contents()
                ks += [
                    "x",                    # execute analysis
                    "st", output_filename,  # stability output to file
                    "",
                    "fs",                   # strip forces to stdout
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

                # Parse stability output (reuse parent's parser)
                output_path = directory / output_filename
                if not output_path.exists():
                    raise FileNotFoundError(
                        "AVL didn't produce stability output. "
                        "Check avl_command and input geometry."
                    )
                with open(output_path) as f:
                    raw = f.read()
                result = self.parse_unformatted_data_output(raw)

                # Post-process standard results (mirrors parent's run())
                result = self._post_process_results(result)

                # Parse strip forces from stdout
                result["strip_forces"] = parse_strip_forces_output(stdout_text)

                return result
            finally:
                if cleanup is not None:
                    cleanup.cleanup()

        def _post_process_results(self, result: dict) -> dict:
            """Apply the same post-processing as the parent's run() method.

            Lowercases standard keys, computes dimensional forces/moments,
            and converts to multiple axis systems.
            """
            import numpy as np

            op = self.op_point
            renames = {
                "Alpha": "alpha", "Beta": "beta", "Mach": "mach",
                "pb/2V": "pb/2V", "qc/2V": "qc/2V", "rb/2V": "rb/2V",
                "p'b/2V": "p'b/2V", "r'b/2V": "r'b/2V",
            }
            for old, new in renames.items():
                if old in result and old != new:
                    result[new] = result.pop(old)

            # Remove 'tot' suffix
            for key in list(result.keys()):
                if key.endswith("tot"):
                    result[key[:-3]] = result.pop(key)

            # Dimensional forces and moments
            q = op.dynamic_pressure()
            S = result.get("Sref", 1)
            c = result.get("Cref", 1)
            b = result.get("Bref", 1)

            CX = result.get("CX", 0)
            CY = result.get("CY", 0)
            CZ = result.get("CZ", 0)
            Cl = result.get("Cl", 0)
            Cm = result.get("Cm", 0)
            Cn = result.get("Cn", 0)

            F_g = q * S * np.array([CX, CY, CZ])
            M_g = q * S * np.array([Cl * b, Cm * c, Cn * b])

            alpha_rad = np.radians(result.get("alpha", 0))
            beta_rad = np.radians(result.get("beta", 0))
            ca, sa = np.cos(alpha_rad), np.sin(alpha_rad)
            cb, sb = np.cos(beta_rad), np.sin(beta_rad)

            a2s = np.array([[ca, 0, sa], [0, 1, 0], [-sa, 0, ca]])
            s2w = np.array([[cb, -sb, 0], [sb, cb, 0], [0, 0, 1]])

            F_b = F_g
            F_s = a2s @ F_b
            F_w = s2w @ F_s
            M_b = M_g
            M_s = a2s @ M_b
            M_w = s2w @ M_s

            result["F_g"] = F_g
            result["F_b"] = F_b
            result["F_w"] = F_w
            result["M_g"] = M_g
            result["M_b"] = M_b
            result["M_w"] = M_w
            result["L"] = -F_w[2]
            result["Y"] = F_w[1]
            result["D"] = -F_w[0]
            result["l_b"] = M_b[0]
            result["m_b"] = M_b[1]
            result["n_b"] = M_b[2]

            V = op.velocity
            result["p"] = result.get("pb/2V", 0) * 2 * V / b if b else 0
            result["q"] = result.get("qc/2V", 0) * 2 * V / c if c else 0
            result["r"] = result.get("rb/2V", 0) * 2 * V / b if b else 0

            if "Clb Cnr / Clr Cnb" not in result:
                Clb = result.get("Clb", 0)
                Cnr = result.get("Cnr", 0)
                Clr = result.get("Clr", 0)
                Cnb = result.get("Cnb", 0)
                denom = Clr * Cnb
                result["Clb Cnr / Clr Cnb"] = (Clb * Cnr / denom) if denom else 0

            return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest app/tests/test_avl_strip_forces.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add app/services/avl_strip_forces.py app/tests/test_avl_strip_forces.py
git commit -m "feat(#140): AVLWithStripForces subclass with stdout capture"
```

---

### Task 3: Pydantic schemas for strip-force response

**Files:**
- Create: `app/schemas/strip_forces.py`
- Modify: `app/schemas/__init__.py`

- [ ] **Step 1: Create schemas**

```python
# app/schemas/strip_forces.py
"""Pydantic schemas for AVL strip-force distribution responses."""

from pydantic import BaseModel, Field


class StripForceEntry(BaseModel):
    j: int = Field(..., description="Strip index")
    x_le: float = Field(..., alias="Xle", description="Strip leading-edge X (m)")
    y_le: float = Field(..., alias="Yle", description="Strip leading-edge Y (m)")
    z_le: float = Field(..., alias="Zle", description="Strip leading-edge Z (m)")
    chord: float = Field(..., alias="Chord", description="Local chord (m)")
    area: float = Field(..., alias="Area", description="Strip area (m²)")
    c_cl: float = Field(..., description="Chord × Cl product")
    ai: float = Field(..., description="Induced angle of attack (rad)")
    cl_norm: float = Field(..., description="Normalized Cl (cl × chord / Cref)")
    cl: float = Field(..., description="Local lift coefficient")
    cd: float = Field(..., description="Local drag coefficient")
    cdv: float = Field(..., description="Local viscous drag coefficient")
    cm_c4: float = Field(..., alias="cm_c/4", description="Moment coefficient at c/4")
    cm_le: float = Field(..., alias="cm_LE", description="Moment coefficient at LE")
    cp_xc: float = Field(..., alias="C.P.x/c", description="Center of pressure x/c")

    model_config = {"populate_by_name": True}


class SurfaceStripForces(BaseModel):
    surface_name: str = Field(..., description="AVL surface name")
    surface_number: int = Field(..., description="AVL surface index")
    n_chordwise: int = Field(..., description="Number of chordwise panels")
    n_spanwise: int = Field(..., description="Number of spanwise strips")
    surface_area: float = Field(..., description="Total surface area (m²)")
    strips: list[StripForceEntry] = Field(..., description="Per-strip force data")


class StripForcesResponse(BaseModel):
    alpha: float = Field(..., description="Angle of attack (deg)")
    mach: float = Field(..., description="Mach number")
    sref: float = Field(..., description="Reference area (m²)")
    cref: float = Field(..., description="Reference chord (m)")
    bref: float = Field(..., description="Reference span (m)")
    surfaces: list[SurfaceStripForces] = Field(..., description="Per-surface strip forces")
```

- [ ] **Step 2: Add export to schemas __init__**

Add to `app/schemas/__init__.py`:

```python
from app.schemas.strip_forces import StripForcesResponse, SurfaceStripForces, StripForceEntry
```

- [ ] **Step 3: Commit**

```bash
git add app/schemas/strip_forces.py app/schemas/__init__.py
git commit -m "feat(#141): Pydantic schemas for strip-force response"
```

---

### Task 4: REST endpoint + integration wiring

**Files:**
- Modify: `app/api/v2/endpoints/aeroanalysis.py`
- Modify: `app/api/utils.py`

- [ ] **Step 1: Read current aeroanalysis endpoint patterns**

Read `app/api/v2/endpoints/aeroanalysis.py` to understand existing endpoint structure and router setup.

- [ ] **Step 2: Add strip_forces endpoint**

Add to `app/api/v2/endpoints/aeroanalysis.py`:

```python
from app.schemas.strip_forces import StripForcesResponse, SurfaceStripForces, StripForceEntry


@router.post(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/strip_forces",
    response_model=StripForcesResponse,
    tags=["analysis"],
    operation_id="get_wing_strip_forces",
)
async def get_wing_strip_forces(
    aeroplane_id: str = Path(..., description="The ID of the aeroplane"),
    wing_name: str = Path(..., description="The name of the wing"),
    operating_point: OperatingPointSchema = Body(...),
    db: Session = Depends(get_db),
):
    """Run AVL analysis and return spanwise strip-force distributions."""
    from app.services.avl_strip_forces import AVLWithStripForces

    aeroplane = get_aeroplane_or_raise(db, aeroplane_id)
    asb_airplane = await aeroplaneSchemaToAsbAirplane_async(
        AeroplaneSchema.model_validate(aeroplane, from_attributes=True)
    )

    op_point = asb.OperatingPoint(
        atmosphere=asb.Atmosphere(altitude=operating_point.altitude),
        velocity=operating_point.velocity,
        alpha=operating_point.alpha,
        beta=operating_point.beta,
    )

    avl_command = str(Path(__file__).resolve().parents[4] / "exports" / "avl")
    asb_airplane.xyz_ref = operating_point.xyz_ref

    avl = AVLWithStripForces(
        airplane=asb_airplane,
        op_point=op_point,
        xyz_ref=operating_point.xyz_ref,
        avl_command=avl_command,
        timeout=30,
    )
    result = avl.run()

    strip_forces_data = result.get("strip_forces", [])

    surfaces = []
    for sf in strip_forces_data:
        strips = [StripForceEntry.model_validate(s) for s in sf["strips"]]
        surfaces.append(SurfaceStripForces(
            surface_name=sf["surface_name"],
            surface_number=sf["surface_number"],
            n_chordwise=sf["n_chordwise"],
            n_spanwise=sf["n_spanwise"],
            surface_area=sf["surface_area"],
            strips=strips,
        ))

    return StripForcesResponse(
        alpha=result.get("alpha", operating_point.alpha),
        mach=result.get("mach", 0),
        sref=result.get("Sref", 0),
        cref=result.get("Cref", 0),
        bref=result.get("Bref", 0),
        surfaces=surfaces,
    )
```

- [ ] **Step 3: Commit**

```bash
git add app/api/v2/endpoints/aeroanalysis.py app/api/utils.py
git commit -m "feat(#142): strip_forces endpoint for spanwise distributions"
```

---

### Task 5: Integration test (slow)

**Files:**
- Create: `app/tests/test_avl_strip_forces_integration.py`

- [ ] **Step 1: Write integration test**

```python
# app/tests/test_avl_strip_forces_integration.py
"""Integration test for AVL strip-force extraction.

Requires the AVL binary at exports/avl and CadQuery.
"""
import pytest
from pathlib import Path

AVL_BINARY = Path(__file__).resolve().parents[2] / "exports" / "avl"
pytestmark = pytest.mark.slow


@pytest.fixture
def simple_airplane():
    import aerosandbox as asb
    return asb.Airplane(
        name="test_plane",
        wings=[
            asb.Wing(
                name="Main Wing",
                symmetric=True,
                xsecs=[
                    asb.WingXSec(xyz_le=[0, 0, 0], chord=0.3, airfoil=asb.Airfoil("naca0012")),
                    asb.WingXSec(xyz_le=[0.02, 0.5, 0], chord=0.2, airfoil=asb.Airfoil("naca0012")),
                ],
            )
        ],
    )


@pytest.fixture
def op_point():
    import aerosandbox as asb
    return asb.OperatingPoint(velocity=20, alpha=5)


class TestAVLWithStripForcesIntegration:
    def test_run_returns_strip_forces(self, simple_airplane, op_point):
        from app.services.avl_strip_forces import AVLWithStripForces

        avl = AVLWithStripForces(
            airplane=simple_airplane,
            op_point=op_point,
            avl_command=str(AVL_BINARY),
            timeout=15,
        )
        result = avl.run()

        # Standard AVL results still present
        assert "CL" in result
        assert "CD" in result
        assert result["CL"] > 0

        # Strip forces present
        assert "strip_forces" in result
        surfaces = result["strip_forces"]
        assert len(surfaces) >= 1

        # Check first surface
        surface = surfaces[0]
        assert surface["surface_name"] == "Main Wing"
        assert len(surface["strips"]) > 0

        # Check strip data is physically plausible
        for strip in surface["strips"]:
            assert strip["Chord"] > 0
            assert strip["cl"] > 0  # positive alpha → positive lift
            assert -1 < strip["Yle"] < 1  # within wingspan

    def test_standard_results_match_parent(self, simple_airplane, op_point):
        """AVLWithStripForces must return the same base results as asb.AVL."""
        import aerosandbox as asb
        from app.services.avl_strip_forces import AVLWithStripForces

        parent_avl = asb.AVL(
            airplane=simple_airplane,
            op_point=op_point,
            avl_command=str(AVL_BINARY),
            timeout=15,
        )
        parent_result = parent_avl.run()

        child_avl = AVLWithStripForces(
            airplane=simple_airplane,
            op_point=op_point,
            avl_command=str(AVL_BINARY),
            timeout=15,
        )
        child_result = child_avl.run()

        # Key aerodynamic coefficients must match
        for key in ["CL", "CD", "Cm", "CLa", "Cma"]:
            assert child_result[key] == pytest.approx(parent_result[key], rel=1e-4), \
                f"{key}: {child_result[key]} != {parent_result[key]}"
```

- [ ] **Step 2: Run integration test**

Run: `poetry run pytest app/tests/test_avl_strip_forces_integration.py -v -m slow`
Expected: 2 passed

- [ ] **Step 3: Commit**

```bash
git add app/tests/test_avl_strip_forces_integration.py
git commit -m "test(#144): AVL strip-forces integration tests"
```

---

### Task 6: Final verification + push

- [ ] **Step 1: Run all fast tests**

Run: `poetry run pytest app/tests/ -m "not slow" -x -q`
Expected: all pass, no regressions

- [ ] **Step 2: Run strip-force tests**

Run: `poetry run pytest app/tests/test_avl_strip_forces.py app/tests/test_avl_strip_forces_integration.py -v`
Expected: all pass

- [ ] **Step 3: Lint**

Run: `poetry run ruff check app/services/avl_strip_forces.py app/schemas/strip_forces.py`
Expected: no issues

- [ ] **Step 4: Push and create PR**

```bash
git push -u github HEAD
gh pr create --base main --title "feat: AVL strip-force distributions endpoint" \
  --body "Closes #140, #141, #142, #143, #144. Part of #40."
```
