# AVL Own Generator + NeuralFoil CDCL + Intelligent Spacing — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Aerosandbox's `write_avl()` with a self-serialising dataclass hierarchy (`AvlGeometryFile`), add NeuralFoil-based per-section profile drag (CDCL), and apply intelligent panel spacing rules.

**Architecture:** New module `app/avl/geometry.py` defines a pure-data dataclass tree where `repr()` emits valid AVL format. `app/services/neuralfoil_cdcl_service.py` computes per-section drag polars via NeuralFoil. The existing `avl_geometry_service.py` and `analysis_service.py` are updated to use the new generator and inject CDCL at analysis time. Spacing optimisation lives in a dedicated function in `app/avl/spacing.py`.

**Tech Stack:** Python dataclasses, NeuralFoil (via `aerosandbox.Airfoil.get_aero_from_neuralfoil`), Pydantic v2, pytest

---

## File Structure

| File | Status | Responsibility |
|------|--------|---------------|
| `app/avl/__init__.py` | **New** | Package init |
| `app/avl/geometry.py` | **New** | AVL dataclass hierarchy (`AvlGeometryFile`, `AvlSurface`, `AvlSection`, etc.) with `__repr__` serialisation |
| `app/avl/spacing.py` | **New** | Intelligent spacing optimisation functions |
| `app/services/neuralfoil_cdcl_service.py` | **New** | NeuralFoil CDCL 3-point fitting service |
| `app/schemas/aeroanalysisschema.py` | **Modify** | Add `CdclConfig` and `SpacingConfig` to `OperatingPointSchema` |
| `app/services/avl_geometry_service.py` | **Modify** | Replace `asb.AVL.write_avl()` with `AvlGeometryFile` builder |
| `app/services/analysis_service.py` | **Modify** | Inject CDCL at analysis time via NeuralFoilCdclService |
| `app/api/utils.py` | **Modify** | Pass configs through to AVL runner |
| `app/tests/test_avl_dataclasses.py` | **New** | Tests for dataclass serialisation |
| `app/tests/test_neuralfoil_cdcl_service.py` | **New** | Tests for CDCL fitting and caching |
| `app/tests/test_avl_spacing.py` | **New** | Tests for spacing optimisation |
| `app/tests/test_avl_generator_integration.py` | **New** | Integration: generate → compare with ASB output |

---

## Task 1: AVL Dataclass Hierarchy — Core Types

**Files:**
- Create: `app/avl/__init__.py`
- Create: `app/avl/geometry.py`
- Test: `app/tests/test_avl_dataclasses.py`

### 1.1 — Write failing tests for `AvlCdcl` serialisation

- [ ] **Step 1: Create test file with AvlCdcl serialisation test**

```python
# app/tests/test_avl_dataclasses.py
"""Tests for AVL geometry dataclass serialisation."""
from __future__ import annotations


class TestAvlCdcl:
    def test_repr_formats_six_values(self):
        from app.avl.geometry import AvlCdcl

        cdcl = AvlCdcl(
            cl_min=-0.6, cd_min=0.024,
            cl_0=0.2, cd_0=0.008,
            cl_max=1.4, cd_max=0.032,
        )
        result = repr(cdcl)
        assert "CDCL" in result
        lines = [l.strip() for l in result.strip().splitlines() if l.strip() and not l.strip().startswith("!")]
        # First non-comment line is the keyword
        assert lines[0] == "CDCL"
        # Second line has 6 values
        values = lines[1].split()
        assert len(values) == 6
        assert float(values[0]) == -0.6
        assert float(values[1]) == 0.024
        assert float(values[4]) == 1.4
        assert float(values[5]) == 0.032

    def test_zero_cdcl_includes_comment(self):
        from app.avl.geometry import AvlCdcl

        cdcl = AvlCdcl.zeros()
        result = repr(cdcl)
        assert "CDCL" in result
        assert "0" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator && poetry run pytest app/tests/test_avl_dataclasses.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.avl'`

- [ ] **Step 3: Create `app/avl/__init__.py` and implement `AvlCdcl`**

```python
# app/avl/__init__.py
```

```python
# app/avl/geometry.py
"""Self-serialising AVL geometry dataclasses.

Each class implements __repr__ to emit its AVL format block.
repr(AvlGeometryFile(...)) produces a complete .avl file string.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AvlCdcl:
    """AVL CDCL (profile drag polar) block — 3-point parabolic fit."""
    cl_min: float
    cd_min: float
    cl_0: float
    cd_0: float
    cl_max: float
    cd_max: float

    @classmethod
    def zeros(cls) -> AvlCdcl:
        return cls(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    def is_zero(self) -> bool:
        return all(v == 0.0 for v in (
            self.cl_min, self.cd_min, self.cl_0, self.cd_0, self.cl_max, self.cd_max
        ))

    def __repr__(self) -> str:
        lines = [
            "CDCL",
            f"!CL1      CD1       CL2       CD2       CL3       CD3",
            f"{self.cl_min:<10g}{self.cd_min:<10g}{self.cl_0:<10g}{self.cd_0:<10g}{self.cl_max:<10g}{self.cd_max:<10g}",
        ]
        return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator && poetry run pytest app/tests/test_avl_dataclasses.py::TestAvlCdcl -v`
Expected: PASS

### 1.2 — Write failing tests for `AvlControl` serialisation

- [ ] **Step 5: Add AvlControl test**

```python
# Append to app/tests/test_avl_dataclasses.py

class TestAvlControl:
    def test_repr_formats_control_block(self):
        from app.avl.geometry import AvlControl

        ctrl = AvlControl(
            name="aileron",
            gain=1.0,
            xhinge=0.8,
            xyz_hvec=(0.0, 0.0, 0.0),
            sgn_dup=-1.0,
        )
        result = repr(ctrl)
        lines = [l.strip() for l in result.strip().splitlines() if l.strip() and not l.strip().startswith("!")]
        assert lines[0] == "CONTROL"
        parts = lines[1].split()
        assert parts[0] == "aileron"
        assert float(parts[1]) == 1.0
        assert float(parts[2]) == 0.8
        assert float(parts[-1]) == -1.0
```

- [ ] **Step 6: Implement `AvlControl`**

```python
# Add to app/avl/geometry.py

@dataclass
class AvlControl:
    """AVL CONTROL block for a control surface."""
    name: str
    gain: float
    xhinge: float
    xyz_hvec: tuple[float, float, float]
    sgn_dup: float

    def __repr__(self) -> str:
        hx, hy, hz = self.xyz_hvec
        return (
            f"CONTROL\n"
            f"!name     gain  Xhinge  Xhvec Yhvec Zhvec  SgnDup\n"
            f"{self.name} {self.gain} {self.xhinge:.8g} {hx} {hy} {hz} {self.sgn_dup:g}"
        )
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator && poetry run pytest app/tests/test_avl_dataclasses.py::TestAvlControl -v`
Expected: PASS

### 1.3 — Write failing tests for airfoil types (`AvlNaca`, `AvlAfile`, `AvlAirfoilInline`)

- [ ] **Step 8: Add airfoil type tests**

```python
# Append to app/tests/test_avl_dataclasses.py

class TestAvlAirfoilTypes:
    def test_naca_repr(self):
        from app.avl.geometry import AvlNaca

        naca = AvlNaca("2412")
        result = repr(naca)
        assert "NACA" in result
        assert "2412" in result

    def test_afile_repr(self):
        from app.avl.geometry import AvlAfile

        afile = AvlAfile("/path/to/airfoil.dat")
        result = repr(afile)
        assert "AFIL" in result
        assert "/path/to/airfoil.dat" in result

    def test_airfoil_inline_repr(self):
        from app.avl.geometry import AvlAirfoilInline

        coords = "1.0 0.0\n0.5 0.05\n0.0 0.0\n0.5 -0.03\n1.0 0.0"
        af = AvlAirfoilInline(name="custom", coordinates=coords)
        result = repr(af)
        assert "AIRFOIL" in result
        assert "1.0 0.0" in result
```

- [ ] **Step 9: Implement airfoil types**

```python
# Add to app/avl/geometry.py

@dataclass
class AvlNaca:
    """AVL NACA keyword — 4 or 5-digit NACA series."""
    digits: str

    def __repr__(self) -> str:
        return f"NACA\n{self.digits}"


@dataclass
class AvlAfile:
    """AVL AFIL keyword — external airfoil coordinate file."""
    filepath: str

    def __repr__(self) -> str:
        return f"AFIL\n{self.filepath}"


@dataclass
class AvlAirfoilInline:
    """AVL AIRFOIL keyword — inline coordinate data."""
    name: str
    coordinates: str

    def __repr__(self) -> str:
        return f"AIRFOIL\n{self.coordinates}"
```

- [ ] **Step 10: Run tests to verify**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator && poetry run pytest app/tests/test_avl_dataclasses.py::TestAvlAirfoilTypes -v`
Expected: PASS

- [ ] **Step 11: Commit**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator
git add app/avl/__init__.py app/avl/geometry.py app/tests/test_avl_dataclasses.py
git commit -m "feat(gh-384): add AVL core dataclasses — AvlCdcl, AvlControl, airfoil types"
```

---

## Task 2: AVL Dataclass Hierarchy — Section and Surface

**Files:**
- Modify: `app/avl/geometry.py`
- Modify: `app/tests/test_avl_dataclasses.py`

### 2.1 — Write failing tests for `AvlSection`

- [ ] **Step 1: Add AvlSection tests**

```python
# Append to app/tests/test_avl_dataclasses.py

class TestAvlSection:
    def test_minimal_section_repr(self):
        from app.avl.geometry import AvlSection

        sec = AvlSection(
            xyz_le=(0.0, 0.0, 0.0),
            chord=0.2,
            ainc=2.0,
        )
        result = repr(sec)
        assert "SECTION" in result
        lines = [l.strip() for l in result.strip().splitlines() if l.strip() and not l.strip().startswith("!") and not l.strip().startswith("#")]
        # SECTION keyword
        assert lines[0] == "SECTION"
        # geometry line: Xle Yle Zle Chord Ainc
        geo = lines[1].split()
        assert len(geo) >= 5
        assert float(geo[0]) == 0.0  # Xle
        assert float(geo[3]) == 0.2  # Chord
        assert float(geo[4]) == 2.0  # Ainc

    def test_section_with_nspan_sspace(self):
        from app.avl.geometry import AvlSection

        sec = AvlSection(
            xyz_le=(0.0, 1.0, 0.0),
            chord=0.15,
            ainc=0.0,
            n_span=8,
            s_space=1.0,
        )
        result = repr(sec)
        geo_lines = [l.strip() for l in result.strip().splitlines()
                     if l.strip() and not l.strip().startswith("!") and not l.strip().startswith("#") and l.strip() != "SECTION"]
        geo = geo_lines[0].split()
        assert len(geo) == 7  # Xle Yle Zle Chord Ainc Nspan Sspace
        assert int(geo[5]) == 8
        assert float(geo[6]) == 1.0

    def test_section_with_airfoil_and_controls(self):
        from app.avl.geometry import AvlSection, AvlAfile, AvlControl, AvlCdcl

        sec = AvlSection(
            xyz_le=(0.01, 0.0, 0.0),
            chord=0.2,
            ainc=0.0,
            airfoil=AvlAfile("/tmp/naca2412.dat"),
            claf=1.1,
            cdcl=AvlCdcl(cl_min=-0.5, cd_min=0.02, cl_0=0.1, cd_0=0.007, cl_max=1.3, cd_max=0.03),
            controls=[
                AvlControl("aileron", 1.0, 0.8, (0.0, 0.0, 0.0), -1.0),
            ],
        )
        result = repr(sec)
        assert "AFIL" in result
        assert "CLAF" in result
        assert "CDCL" in result
        assert "CONTROL" in result
        assert "aileron" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator && poetry run pytest app/tests/test_avl_dataclasses.py::TestAvlSection -v`
Expected: FAIL — `ImportError: cannot import name 'AvlSection'`

- [ ] **Step 3: Implement `AvlSection`**

```python
# Add to app/avl/geometry.py

AvlAirfoil = AvlNaca | AvlAirfoilInline | AvlAfile


@dataclass
class AvlDesign:
    """AVL DESIGN variable."""
    name: str
    weight: float

    def __repr__(self) -> str:
        return f"DESIGN\n{self.name} {self.weight:g}"


@dataclass
class AvlSection:
    """AVL SECTION block for a wing cross-section."""
    xyz_le: tuple[float, float, float]
    chord: float
    ainc: float = 0.0
    n_span: int | None = None
    s_space: float | None = None
    airfoil: AvlAirfoil | None = None
    claf: float | None = None
    cdcl: AvlCdcl | None = None
    controls: list[AvlControl] = field(default_factory=list)
    designs: list[AvlDesign] = field(default_factory=list)

    def __repr__(self) -> str:
        x, y, z = self.xyz_le
        geo = f"{x:.8g} {y:.8g} {z:.8g} {self.chord:.8g} {self.ainc:.8g}"
        if self.n_span is not None and self.s_space is not None:
            geo += f"   {self.n_span}   {self.s_space:g}"

        parts = [
            "SECTION",
            f"!Xle      Yle       Zle       Chord     Ainc  [Nspan  Sspace]",
            geo,
        ]

        if self.airfoil is not None:
            parts.append("")
            parts.append(repr(self.airfoil))

        if self.claf is not None:
            parts.append("")
            parts.append(f"CLAF\n{self.claf:g}")

        if self.cdcl is not None:
            parts.append("")
            parts.append(repr(self.cdcl))

        for ctrl in self.controls:
            parts.append("")
            parts.append(repr(ctrl))

        for design in self.designs:
            parts.append("")
            parts.append(repr(design))

        return "\n".join(parts)
```

- [ ] **Step 4: Run tests to verify**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator && poetry run pytest app/tests/test_avl_dataclasses.py::TestAvlSection -v`
Expected: PASS

### 2.2 — Write failing tests for `AvlSurface`

- [ ] **Step 5: Add AvlSurface tests**

```python
# Append to app/tests/test_avl_dataclasses.py

class TestAvlSurface:
    def test_minimal_surface_repr(self):
        from app.avl.geometry import AvlSurface, AvlSection

        surf = AvlSurface(
            name="Main Wing",
            n_chord=12,
            c_space=1.0,
            sections=[
                AvlSection(xyz_le=(0.0, 0.0, 0.0), chord=0.2),
                AvlSection(xyz_le=(0.02, 1.0, 0.1), chord=0.15),
            ],
        )
        result = repr(surf)
        assert "SURFACE" in result
        assert "Main Wing" in result
        # Must have 2 SECTION keywords
        assert result.count("SECTION") == 2

    def test_surface_with_yduplicate(self):
        from app.avl.geometry import AvlSurface, AvlSection

        surf = AvlSurface(
            name="Wing",
            n_chord=12,
            c_space=1.0,
            yduplicate=0.0,
            sections=[
                AvlSection(xyz_le=(0.0, 0.0, 0.0), chord=0.2),
                AvlSection(xyz_le=(0.0, 1.0, 0.0), chord=0.15),
            ],
        )
        result = repr(surf)
        assert "YDUPLICATE" in result

    def test_surface_with_component(self):
        from app.avl.geometry import AvlSurface, AvlSection

        surf = AvlSurface(
            name="Wing",
            n_chord=12,
            c_space=1.0,
            component=1,
            sections=[
                AvlSection(xyz_le=(0.0, 0.0, 0.0), chord=0.2),
                AvlSection(xyz_le=(0.0, 1.0, 0.0), chord=0.15),
            ],
        )
        result = repr(surf)
        assert "COMPONENT" in result

    def test_surface_with_nspan_sspace(self):
        from app.avl.geometry import AvlSurface, AvlSection

        surf = AvlSurface(
            name="Wing",
            n_chord=12,
            c_space=1.0,
            n_span=20,
            s_space=1.0,
            sections=[
                AvlSection(xyz_le=(0.0, 0.0, 0.0), chord=0.2),
                AvlSection(xyz_le=(0.0, 1.0, 0.0), chord=0.15),
            ],
        )
        result = repr(surf)
        # Spacing line should contain Nchord Cspace Nspan Sspace
        lines = result.splitlines()
        spacing_line = None
        for i, line in enumerate(lines):
            if "Nchordwise" in line or "Nchord" in line:
                spacing_line = lines[i + 1].strip()
                break
        assert spacing_line is not None
        parts = spacing_line.split()
        assert len(parts) == 4
        assert int(parts[0]) == 12
        assert int(parts[2]) == 20

    def test_surface_flags_nowake_noalbe_noload(self):
        from app.avl.geometry import AvlSurface, AvlSection

        surf = AvlSurface(
            name="Fin",
            n_chord=8,
            c_space=1.0,
            nowake=True,
            noalbe=True,
            noload=True,
            sections=[
                AvlSection(xyz_le=(0.0, 0.0, 0.0), chord=0.1),
                AvlSection(xyz_le=(0.0, 0.0, 0.3), chord=0.08),
            ],
        )
        result = repr(surf)
        assert "NOWAKE" in result
        assert "NOALBE" in result
        assert "NOLOAD" in result
```

- [ ] **Step 6: Implement `AvlSurface`**

```python
# Add to app/avl/geometry.py

@dataclass
class AvlSurface:
    """AVL SURFACE block."""
    name: str
    n_chord: int
    c_space: float
    n_span: int | None = None
    s_space: float | None = None
    yduplicate: float | None = None
    component: int | None = None
    scale: tuple[float, float, float] | None = None
    translate: tuple[float, float, float] | None = None
    angle: float | None = None
    nowake: bool = False
    noalbe: bool = False
    noload: bool = False
    cdcl: AvlCdcl | None = None
    sections: list[AvlSection] = field(default_factory=list)

    def __repr__(self) -> str:
        spacing = f"{self.n_chord}   {self.c_space:g}"
        if self.n_span is not None and self.s_space is not None:
            spacing += f"   {self.n_span}   {self.s_space:g}"

        parts = [
            f"#{'=' * 79}",
            "SURFACE",
            self.name,
            "!Nchordwise  Cspace  [Nspanwise  Sspace]",
            spacing,
        ]

        if self.component is not None:
            parts += ["", "COMPONENT", str(self.component)]

        if self.yduplicate is not None:
            parts += ["", "YDUPLICATE", f"{self.yduplicate:g}"]

        if self.scale is not None:
            sx, sy, sz = self.scale
            parts += ["", "SCALE", f"{sx:g} {sy:g} {sz:g}"]

        if self.translate is not None:
            tx, ty, tz = self.translate
            parts += ["", "TRANSLATE", f"{tx:.8g} {ty:.8g} {tz:.8g}"]

        if self.angle is not None:
            parts += ["", "ANGLE", f"{self.angle:g}"]

        if self.nowake:
            parts += ["", "NOWAKE"]
        if self.noalbe:
            parts += ["", "NOALBE"]
        if self.noload:
            parts += ["", "NOLOAD"]

        if self.cdcl is not None:
            parts += ["", repr(self.cdcl)]

        for sec in self.sections:
            parts += ["", f"#{'-' * 50}", repr(sec)]

        return "\n".join(parts)
```

- [ ] **Step 7: Run tests to verify**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator && poetry run pytest app/tests/test_avl_dataclasses.py::TestAvlSurface -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator
git add app/avl/geometry.py app/tests/test_avl_dataclasses.py
git commit -m "feat(gh-384): add AvlSection and AvlSurface dataclasses with serialisation"
```

---

## Task 3: AVL Dataclass Hierarchy — Top-Level File, Body, and Symmetry

**Files:**
- Modify: `app/avl/geometry.py`
- Modify: `app/tests/test_avl_dataclasses.py`

### 3.1 — Write failing tests for `AvlSymmetry`, `AvlReference`, `AvlBody`, `AvlGeometryFile`

- [ ] **Step 1: Add top-level tests**

```python
# Append to app/tests/test_avl_dataclasses.py

class TestAvlBody:
    def test_body_repr(self):
        from app.avl.geometry import AvlBody

        body = AvlBody(
            name="Fuselage",
            n_body=12,
            b_space=1.0,
            bfile="/tmp/fuselage.bfile",
        )
        result = repr(body)
        assert "BODY" in result
        assert "Fuselage" in result
        assert "BFIL" in result
        assert "/tmp/fuselage.bfile" in result

    def test_body_with_translate_and_yduplicate(self):
        from app.avl.geometry import AvlBody

        body = AvlBody(
            name="Nacelle",
            n_body=8,
            b_space=1.0,
            bfile="/tmp/nacelle.bfile",
            yduplicate=0.0,
            translate=(1.0, 0.5, 0.0),
        )
        result = repr(body)
        assert "YDUPLICATE" in result
        assert "TRANSLATE" in result


class TestAvlGeometryFile:
    def test_complete_file_structure(self):
        from app.avl.geometry import (
            AvlGeometryFile, AvlSymmetry, AvlReference,
            AvlSurface, AvlSection, AvlAfile, AvlCdcl,
        )

        avl_file = AvlGeometryFile(
            title="Test Aircraft",
            mach=0.0,
            symmetry=AvlSymmetry(iy_sym=0, iz_sym=0, z_sym=0.0),
            reference=AvlReference(
                s_ref=0.5,
                c_ref=0.2,
                b_ref=2.0,
                xyz_ref=(0.05, 0.0, 0.0),
            ),
            surfaces=[
                AvlSurface(
                    name="Wing",
                    n_chord=12,
                    c_space=1.0,
                    yduplicate=0.0,
                    sections=[
                        AvlSection(
                            xyz_le=(0.0, 0.0, 0.0),
                            chord=0.2,
                            airfoil=AvlAfile("/tmp/naca2412.dat"),
                        ),
                        AvlSection(
                            xyz_le=(0.02, 1.0, 0.1),
                            chord=0.15,
                            airfoil=AvlAfile("/tmp/naca2412.dat"),
                        ),
                    ],
                ),
            ],
        )
        result = repr(avl_file)
        lines = result.splitlines()
        # First line is the title
        assert lines[0] == "Test Aircraft"
        # Must contain Mach, symmetry, reference, surface
        assert "Mach" in result or "0" in lines[1]  # Mach line
        assert "Sref" in result or "0.5" in result
        assert "SURFACE" in result
        assert "SECTION" in result

    def test_file_with_cdp(self):
        from app.avl.geometry import (
            AvlGeometryFile, AvlSymmetry, AvlReference, AvlSurface, AvlSection,
        )

        avl_file = AvlGeometryFile(
            title="Test",
            mach=0.1,
            symmetry=AvlSymmetry(iy_sym=0, iz_sym=0, z_sym=0.0),
            reference=AvlReference(
                s_ref=1.0, c_ref=0.3, b_ref=3.0, xyz_ref=(0.0, 0.0, 0.0),
            ),
            cdp=0.01,
            surfaces=[
                AvlSurface(name="W", n_chord=8, c_space=1.0, sections=[
                    AvlSection(xyz_le=(0.0, 0.0, 0.0), chord=0.3),
                    AvlSection(xyz_le=(0.0, 1.5, 0.0), chord=0.2),
                ]),
            ],
        )
        result = repr(avl_file)
        assert "CDp" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator && poetry run pytest app/tests/test_avl_dataclasses.py::TestAvlBody app/tests/test_avl_dataclasses.py::TestAvlGeometryFile -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement `AvlSymmetry`, `AvlReference`, `AvlBody`, `AvlGeometryFile`**

```python
# Add to app/avl/geometry.py

@dataclass
class AvlSymmetry:
    """AVL symmetry configuration."""
    iy_sym: int = 0
    iz_sym: int = 0
    z_sym: float = 0.0

    def __repr__(self) -> str:
        return (
            f"!IYsym  IZsym  Zsym\n"
            f"{self.iy_sym}   {self.iz_sym}   {self.z_sym:g}"
        )


@dataclass
class AvlReference:
    """AVL reference quantities."""
    s_ref: float
    c_ref: float
    b_ref: float
    xyz_ref: tuple[float, float, float]

    def __repr__(self) -> str:
        x, y, z = self.xyz_ref
        return (
            f"!Sref    Cref    Bref\n"
            f"{self.s_ref:.8g} {self.c_ref:.8g} {self.b_ref:.8g}\n"
            f"!Xref    Yref    Zref\n"
            f"{x:.8g} {y:.8g} {z:.8g}"
        )


@dataclass
class AvlBody:
    """AVL BODY block."""
    name: str
    n_body: int
    b_space: float
    bfile: str
    yduplicate: float | None = None
    scale: tuple[float, float, float] | None = None
    translate: tuple[float, float, float] | None = None

    def __repr__(self) -> str:
        parts = [
            f"#{'=' * 50}",
            "BODY",
            self.name,
            f"{self.n_body}   {self.b_space:g}",
        ]

        if self.yduplicate is not None:
            parts += ["", "YDUPLICATE", f"{self.yduplicate:g}"]

        if self.scale is not None:
            sx, sy, sz = self.scale
            parts += ["", "SCALE", f"{sx:g} {sy:g} {sz:g}"]

        if self.translate is not None:
            tx, ty, tz = self.translate
            parts += ["", "TRANSLATE", f"{tx:.8g} {ty:.8g} {tz:.8g}"]

        parts += ["", "BFIL", self.bfile]

        return "\n".join(parts)


@dataclass
class AvlGeometryFile:
    """Complete AVL geometry file. repr() produces the full .avl content."""
    title: str
    mach: float
    symmetry: AvlSymmetry
    reference: AvlReference
    surfaces: list[AvlSurface] = field(default_factory=list)
    bodies: list[AvlBody] = field(default_factory=list)
    cdp: float = 0.0

    def __repr__(self) -> str:
        parts = [
            self.title,
            "!Mach",
            f"{self.mach:g}",
            repr(self.symmetry),
            repr(self.reference),
            "!CDp",
            f"{self.cdp:g}",
        ]

        for surf in self.surfaces:
            parts += ["", repr(surf)]

        for body in self.bodies:
            parts += ["", repr(body)]

        return "\n".join(parts)
```

- [ ] **Step 4: Run tests to verify**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator && poetry run pytest app/tests/test_avl_dataclasses.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator
git add app/avl/geometry.py app/tests/test_avl_dataclasses.py
git commit -m "feat(gh-384): complete AVL dataclass hierarchy — Body, Symmetry, Reference, GeometryFile"
```

---

## Task 4: NeuralFoil CDCL Service

**Files:**
- Create: `app/services/neuralfoil_cdcl_service.py`
- Test: `app/tests/test_neuralfoil_cdcl_service.py`

### 4.1 — Write failing tests for `CdclConfig` and `SpacingConfig` schemas

- [ ] **Step 1: Add config schemas to aeroanalysisschema.py — write test first**

```python
# app/tests/test_neuralfoil_cdcl_service.py
"""Tests for NeuralFoil CDCL service."""
from __future__ import annotations


class TestCdclConfig:
    def test_defaults(self):
        from app.schemas.aeroanalysisschema import CdclConfig

        config = CdclConfig()
        assert config.alpha_start_deg == -10.0
        assert config.alpha_end_deg == 16.0
        assert config.alpha_step_deg == 1.0
        assert config.model_size == "large"
        assert config.n_crit == 9.0

    def test_custom_values(self):
        from app.schemas.aeroanalysisschema import CdclConfig

        config = CdclConfig(alpha_start_deg=-5.0, alpha_end_deg=12.0, n_crit=11.0)
        assert config.alpha_start_deg == -5.0
        assert config.n_crit == 11.0


class TestSpacingConfig:
    def test_defaults(self):
        from app.schemas.aeroanalysisschema import SpacingConfig

        config = SpacingConfig()
        assert config.n_chord == 12
        assert config.c_space == 1.0
        assert config.n_span == 20
        assert config.s_space == 1.0
        assert config.auto_optimise is True

    def test_auto_optimise_false(self):
        from app.schemas.aeroanalysisschema import SpacingConfig

        config = SpacingConfig(auto_optimise=False)
        assert config.auto_optimise is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator && poetry run pytest app/tests/test_neuralfoil_cdcl_service.py::TestCdclConfig app/tests/test_neuralfoil_cdcl_service.py::TestSpacingConfig -v`
Expected: FAIL — `ImportError: cannot import name 'CdclConfig'`

- [ ] **Step 3: Add CdclConfig and SpacingConfig to aeroanalysisschema.py**

Add before `OperatingPointSchema`:

```python
class CdclConfig(BaseModel):
    """Configuration for NeuralFoil CDCL profile-drag computation."""
    alpha_start_deg: float = Field(-10.0, description="Start of alpha sweep in degrees")
    alpha_end_deg: float = Field(16.0, description="End of alpha sweep in degrees")
    alpha_step_deg: float = Field(1.0, description="Alpha step size in degrees")
    model_size: str = Field("large", description="NeuralFoil model size")
    n_crit: float = Field(9.0, description="Critical amplification ratio for transition")
    xtr_upper: float = Field(1.0, description="Upper surface forced transition location (0-1)")
    xtr_lower: float = Field(1.0, description="Lower surface forced transition location (0-1)")
    include_360_deg_effects: bool = Field(False, description="Include 360-degree post-stall effects")


class SpacingConfig(BaseModel):
    """Configuration for AVL panel spacing optimisation."""
    n_chord: int = Field(12, description="Base chordwise panel count")
    c_space: float = Field(1.0, description="Chordwise spacing distribution (1=cosine)")
    n_span: int = Field(20, description="Base spanwise panel count")
    s_space: float = Field(1.0, description="Spanwise spacing distribution (1=cosine)")
    auto_optimise: bool = Field(True, description="Apply intelligent spacing rules automatically")
```

Add optional fields to `OperatingPointSchema`:

```python
    cdcl_config: Optional[CdclConfig] = Field(None, description="NeuralFoil CDCL configuration")
    spacing_config: Optional[SpacingConfig] = Field(None, description="AVL panel spacing configuration")
```

- [ ] **Step 4: Run tests to verify**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator && poetry run pytest app/tests/test_neuralfoil_cdcl_service.py::TestCdclConfig app/tests/test_neuralfoil_cdcl_service.py::TestSpacingConfig -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator
git add app/schemas/aeroanalysisschema.py app/tests/test_neuralfoil_cdcl_service.py
git commit -m "feat(gh-384): add CdclConfig and SpacingConfig schemas to OperatingPointSchema"
```

### 4.2 — Write failing tests for CDCL computation

- [ ] **Step 6: Add NeuralFoilCdclService tests**

```python
# Append to app/tests/test_neuralfoil_cdcl_service.py

import numpy as np
import aerosandbox as asb


class TestNeuralFoilCdclService:
    def test_compute_cdcl_returns_avl_cdcl(self):
        from app.avl.geometry import AvlCdcl
        from app.schemas.aeroanalysisschema import CdclConfig
        from app.services.neuralfoil_cdcl_service import NeuralFoilCdclService

        service = NeuralFoilCdclService()
        airfoil = asb.Airfoil("naca2412")
        config = CdclConfig()

        result = service.compute_cdcl(airfoil, re=500_000.0, mach=0.1, config=config)

        assert isinstance(result, AvlCdcl)
        # Profile drag should be positive
        assert result.cd_0 > 0
        assert result.cd_min > 0
        assert result.cd_max > 0
        # CL ordering: cl_min < cl_0 < cl_max
        assert result.cl_min < result.cl_0 < result.cl_max
        # CD ordering: cd_0 is the minimum
        assert result.cd_0 <= result.cd_min
        assert result.cd_0 <= result.cd_max

    def test_compute_cdcl_different_re_gives_different_results(self):
        from app.schemas.aeroanalysisschema import CdclConfig
        from app.services.neuralfoil_cdcl_service import NeuralFoilCdclService

        service = NeuralFoilCdclService()
        airfoil = asb.Airfoil("naca2412")
        config = CdclConfig()

        result_low_re = service.compute_cdcl(airfoil, re=100_000.0, mach=0.1, config=config)
        result_high_re = service.compute_cdcl(airfoil, re=1_000_000.0, mach=0.1, config=config)

        # Higher Re should give lower minimum drag
        assert result_high_re.cd_0 < result_low_re.cd_0

    def test_cache_reuses_results(self):
        from app.schemas.aeroanalysisschema import CdclConfig
        from app.services.neuralfoil_cdcl_service import NeuralFoilCdclService

        service = NeuralFoilCdclService()
        airfoil = asb.Airfoil("naca0012")
        config = CdclConfig()

        result1 = service.compute_cdcl(airfoil, re=500_000.0, mach=0.1, config=config)
        result2 = service.compute_cdcl(airfoil, re=500_000.0, mach=0.1, config=config)

        # Same object from cache
        assert result1.cd_0 == result2.cd_0
        assert result1.cl_max == result2.cl_max

    def test_compute_reynolds_number(self):
        from app.services.neuralfoil_cdcl_service import compute_reynolds_number

        re = compute_reynolds_number(velocity=30.0, chord=0.2, altitude=0.0)
        # At sea level: ν ≈ 1.46e-5 m²/s → Re ≈ 30 * 0.2 / 1.46e-5 ≈ 411_000
        assert 350_000 < re < 500_000
```

- [ ] **Step 7: Implement NeuralFoilCdclService**

```python
# app/services/neuralfoil_cdcl_service.py
"""NeuralFoil-based CDCL (profile drag polar) computation for AVL sections."""
from __future__ import annotations

import logging
from functools import lru_cache

import aerosandbox as asb
import numpy as np

from app.avl.geometry import AvlCdcl
from app.schemas.aeroanalysisschema import CdclConfig

logger = logging.getLogger(__name__)


def compute_reynolds_number(velocity: float, chord: float, altitude: float) -> float:
    """Compute Reynolds number from flight conditions and section chord."""
    atm = asb.Atmosphere(altitude=altitude)
    return velocity * chord / atm.kinematic_viscosity()


class NeuralFoilCdclService:
    """Compute per-section CDCL via NeuralFoil 3-point fitting."""

    def compute_cdcl(
        self,
        airfoil: asb.Airfoil,
        re: float,
        mach: float,
        config: CdclConfig,
    ) -> AvlCdcl:
        alphas, CLs, CDs = self._get_polar_cached(
            airfoil_name=airfoil.name,
            airfoil=airfoil,
            re=re,
            mach=mach,
            config=config,
        )

        # Point 2 (drag bucket): minimum CD
        idx_cd_min = int(np.argmin(CDs))
        cl_0 = float(CLs[idx_cd_min])
        cd_0 = float(CDs[idx_cd_min])

        # Point 3 (positive stall): maximum CL
        idx_cl_max = int(np.argmax(CLs))
        cl_max = float(CLs[idx_cl_max])
        cd_max = float(CDs[idx_cl_max])

        # Point 1 (negative stall): minimum CL
        idx_cl_min = int(np.argmin(CLs))
        cl_min = float(CLs[idx_cl_min])
        cd_min = float(CDs[idx_cl_min])

        return AvlCdcl(
            cl_min=cl_min, cd_min=cd_min,
            cl_0=cl_0, cd_0=cd_0,
            cl_max=cl_max, cd_max=cd_max,
        )

    @lru_cache(maxsize=128)
    def _get_polar_cached(
        self,
        airfoil_name: str,
        airfoil: asb.Airfoil,
        re: float,
        mach: float,
        config: CdclConfig,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        alphas = np.arange(
            config.alpha_start_deg,
            config.alpha_end_deg + config.alpha_step_deg / 2,
            config.alpha_step_deg,
        )

        aero = airfoil.get_aero_from_neuralfoil(
            alpha=alphas,
            Re=re,
            mach=mach,
            model_size=config.model_size,
            n_crit=config.n_crit,
        )

        CLs = np.atleast_1d(aero["CL"])
        CDs = np.atleast_1d(aero["CD"])

        return alphas, CLs, CDs
```

Note: `lru_cache` requires hashable arguments. `CdclConfig` is a Pydantic model (which is hashable by default). `asb.Airfoil` is not hashable — the `airfoil_name` parameter serves as the cache key while `airfoil` is passed for the actual computation. The `@lru_cache` on this method with `self` means each `NeuralFoilCdclService` instance gets its own cache. The `airfoil` parameter is part of the signature and included in the hash — **we need to make `asb.Airfoil` hashable or use a workaround**.

**Workaround:** Extract the polar data into a standalone cached function keyed only on hashable params:

```python
@lru_cache(maxsize=128)
def _get_polar_data(
    airfoil_name: str,
    airfoil_coordinates_hash: int,
    re: float,
    mach: float,
    alpha_start: float,
    alpha_end: float,
    alpha_step: float,
    model_size: str,
    n_crit: float,
) -> tuple:
    """Module-level cached function — keyed on hashable primitives only."""
    airfoil = asb.Airfoil(name=airfoil_name)
    alphas = np.arange(alpha_start, alpha_end + alpha_step / 2, alpha_step)

    aero = airfoil.get_aero_from_neuralfoil(
        alpha=alphas,
        Re=re,
        mach=mach,
        model_size=model_size,
        n_crit=n_crit,
    )

    CLs = np.atleast_1d(aero["CL"])
    CDs = np.atleast_1d(aero["CD"])

    return tuple(alphas), tuple(CLs.tolist()), tuple(CDs.tolist())
```

Update `compute_cdcl` to call this cached function. The service class becomes a thin wrapper:

```python
class NeuralFoilCdclService:

    def compute_cdcl(
        self,
        airfoil: asb.Airfoil,
        re: float,
        mach: float,
        config: CdclConfig,
    ) -> AvlCdcl:
        coords_hash = hash(tuple(airfoil.coordinates.flatten())) if airfoil.coordinates is not None else 0

        alphas, cl_list, cd_list = _get_polar_data(
            airfoil_name=airfoil.name,
            airfoil_coordinates_hash=coords_hash,
            re=re,
            mach=mach,
            alpha_start=config.alpha_start_deg,
            alpha_end=config.alpha_end_deg,
            alpha_step=config.alpha_step_deg,
            model_size=config.model_size,
            n_crit=config.n_crit,
        )

        CLs = np.array(cl_list)
        CDs = np.array(cd_list)

        idx_cd_min = int(np.argmin(CDs))
        cl_0 = CLs[idx_cd_min]
        cd_0 = CDs[idx_cd_min]

        idx_cl_max = int(np.argmax(CLs))
        cl_max = CLs[idx_cl_max]
        cd_max = CDs[idx_cl_max]

        idx_cl_min = int(np.argmin(CLs))
        cl_min = CLs[idx_cl_min]
        cd_min = CDs[idx_cl_min]

        return AvlCdcl(
            cl_min=float(cl_min), cd_min=float(cd_min),
            cl_0=float(cl_0), cd_0=float(cd_0),
            cl_max=float(cl_max), cd_max=float(cd_max),
        )
```

- [ ] **Step 8: Run tests to verify**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator && poetry run pytest app/tests/test_neuralfoil_cdcl_service.py::TestNeuralFoilCdclService -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator
git add app/services/neuralfoil_cdcl_service.py app/tests/test_neuralfoil_cdcl_service.py
git commit -m "feat(gh-384): add NeuralFoilCdclService with 3-point CDCL fitting and caching"
```

---

## Task 5: Intelligent Spacing Optimisation

**Files:**
- Create: `app/avl/spacing.py`
- Test: `app/tests/test_avl_spacing.py`

### 5.1 — Write failing tests for spacing rules

- [ ] **Step 1: Write spacing tests**

```python
# app/tests/test_avl_spacing.py
"""Tests for intelligent AVL spacing optimisation."""
from __future__ import annotations

from app.avl.geometry import AvlControl, AvlSection, AvlSurface
from app.schemas.aeroanalysisschema import SpacingConfig


class TestControlSurfaceDetection:
    def test_increases_nchord_when_controls_present(self):
        from app.avl.spacing import optimise_surface_spacing

        surface = AvlSurface(
            name="Wing",
            n_chord=12,
            c_space=1.0,
            n_span=20,
            s_space=1.0,
            sections=[
                AvlSection(
                    xyz_le=(0.0, 0.0, 0.0), chord=0.2,
                    controls=[AvlControl("aileron", 1.0, 0.8, (0.0, 0.0, 0.0), -1.0)],
                ),
                AvlSection(xyz_le=(0.0, 1.0, 0.0), chord=0.15),
            ],
        )
        config = SpacingConfig(n_chord=12, auto_optimise=True)
        result = optimise_surface_spacing(surface, config)
        assert result.n_chord >= 16

    def test_no_increase_without_controls(self):
        from app.avl.spacing import optimise_surface_spacing

        surface = AvlSurface(
            name="Wing",
            n_chord=12,
            c_space=1.0,
            n_span=20,
            s_space=1.0,
            sections=[
                AvlSection(xyz_le=(0.0, 0.0, 0.0), chord=0.2),
                AvlSection(xyz_le=(0.0, 1.0, 0.0), chord=0.15),
            ],
        )
        config = SpacingConfig(n_chord=12, auto_optimise=True)
        result = optimise_surface_spacing(surface, config)
        assert result.n_chord == 12


class TestAutoOptimiseDisabled:
    def test_base_values_preserved_when_disabled(self):
        from app.avl.spacing import optimise_surface_spacing

        surface = AvlSurface(
            name="Wing",
            n_chord=8,
            c_space=1.0,
            n_span=10,
            s_space=1.0,
            sections=[
                AvlSection(
                    xyz_le=(0.0, 0.0, 0.0), chord=0.2,
                    controls=[AvlControl("aileron", 1.0, 0.8, (0.0, 0.0, 0.0), -1.0)],
                ),
                AvlSection(xyz_le=(0.0, 1.0, 0.0), chord=0.15),
            ],
        )
        config = SpacingConfig(n_chord=8, n_span=10, auto_optimise=False)
        result = optimise_surface_spacing(surface, config)
        assert result.n_chord == 8
        assert result.n_span == 10


class TestUnsweptWingSpacing:
    def test_unswept_wing_uses_neg_sine(self):
        from app.avl.spacing import optimise_surface_spacing

        surface = AvlSurface(
            name="Wing",
            n_chord=12,
            c_space=1.0,
            n_span=20,
            s_space=1.0,
            sections=[
                AvlSection(xyz_le=(0.0, 0.0, 0.0), chord=0.2),
                AvlSection(xyz_le=(0.0, 1.0, 0.0), chord=0.15),
            ],
        )
        config = SpacingConfig(auto_optimise=True)
        result = optimise_surface_spacing(surface, config)
        assert result.s_space == -2.0

    def test_swept_wing_keeps_cosine(self):
        from app.avl.spacing import optimise_surface_spacing

        surface = AvlSurface(
            name="Wing",
            n_chord=12,
            c_space=1.0,
            n_span=20,
            s_space=1.0,
            sections=[
                AvlSection(xyz_le=(0.0, 0.0, 0.0), chord=0.3),
                AvlSection(xyz_le=(0.15, 1.0, 0.0), chord=0.2),
            ],
        )
        config = SpacingConfig(auto_optimise=True)
        result = optimise_surface_spacing(surface, config)
        assert result.s_space == 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator && poetry run pytest app/tests/test_avl_spacing.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement spacing optimisation**

```python
# app/avl/spacing.py
"""Intelligent AVL panel spacing optimisation based on geometry features."""
from __future__ import annotations

import copy
import math

from app.avl.geometry import AvlSurface
from app.schemas.aeroanalysisschema import SpacingConfig


def _has_control_surfaces(surface: AvlSurface) -> bool:
    return any(sec.controls for sec in surface.sections)


def _is_unswept(surface: AvlSurface, threshold_deg: float = 5.0) -> bool:
    """Check if the wing has negligible sweep (leading-edge x-offset vs span)."""
    if len(surface.sections) < 2:
        return True
    root = surface.sections[0]
    tip = surface.sections[-1]
    dx = abs(tip.xyz_le[0] - root.xyz_le[0])
    dy = abs(tip.xyz_le[1] - root.xyz_le[1])
    dz = abs(tip.xyz_le[2] - root.xyz_le[2])
    span = math.sqrt(dy**2 + dz**2)
    if span < 1e-9:
        return True
    sweep_rad = math.atan2(dx, span)
    return math.degrees(sweep_rad) < threshold_deg


def _has_centreline_break(surface: AvlSurface) -> bool:
    """Check if any section sits at the centreline (y=0) mid-span."""
    if len(surface.sections) <= 2:
        return False
    for sec in surface.sections[1:-1]:
        if abs(sec.xyz_le[1]) < 1e-6:
            return True
    return False


def optimise_surface_spacing(
    surface: AvlSurface,
    config: SpacingConfig,
) -> AvlSurface:
    """Apply intelligent spacing rules to a surface, returning a modified copy."""
    result = copy.copy(surface)
    result.n_chord = config.n_chord
    result.c_space = config.c_space
    result.n_span = config.n_span
    result.s_space = config.s_space

    if not config.auto_optimise:
        return result

    if _has_control_surfaces(surface):
        result.n_chord = max(result.n_chord, 16)

    if _is_unswept(surface) and not _has_centreline_break(surface):
        result.s_space = -2.0

    return result
```

- [ ] **Step 4: Run tests to verify**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator && poetry run pytest app/tests/test_avl_spacing.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator
git add app/avl/spacing.py app/tests/test_avl_spacing.py
git commit -m "feat(gh-384): add intelligent AVL spacing optimisation with control surface and sweep detection"
```

---

## Task 6: AVL Geometry Builder — Replace `asb.AVL.write_avl()`

**Files:**
- Modify: `app/services/avl_geometry_service.py`
- Test: `app/tests/test_avl_generator_integration.py`

This task replaces the current `generate_avl_content()` function that delegates to `asb.AVL.write_avl()` with a new function that builds an `AvlGeometryFile` from the `AeroplaneSchema`.

### 6.1 — Write builder function and integration test

- [ ] **Step 1: Write integration test comparing new generator vs old**

```python
# app/tests/test_avl_generator_integration.py
"""Integration tests for the AVL geometry builder."""
from __future__ import annotations

import aerosandbox as asb

from app.avl.geometry import AvlGeometryFile
from app.schemas.aeroanalysisschema import SpacingConfig


class TestBuildAvlGeometryFile:
    def _make_plane_schema(self):
        """Create a minimal AeroplaneSchema for testing."""
        from collections import OrderedDict
        from app.schemas.aeroplaneschema import (
            AeroplaneSchema, AsbWingSchema, WingXSecSchema,
            ControlSurfaceSchema,
        )

        return AeroplaneSchema(
            name="TestPlane",
            wings=OrderedDict({
                "Main Wing": AsbWingSchema(
                    name="Main Wing",
                    symmetric=True,
                    x_secs=[
                        WingXSecSchema(
                            xyz_le=[0.0, 0.0, 0.0],
                            chord=0.2,
                            twist=2.0,
                            airfoil="naca2412",
                            control_surface=ControlSurfaceSchema(
                                name="aileron",
                                hinge_point=0.75,
                                symmetric=False,
                                deflection=0.0,
                            ),
                        ),
                        WingXSecSchema(
                            xyz_le=[0.02, 1.0, 0.1],
                            chord=0.15,
                            twist=0.0,
                            airfoil="naca2412",
                        ),
                    ],
                ),
            }),
            xyz_ref=[0.05, 0.0, 0.0],
        )

    def test_build_produces_valid_avl_file(self):
        from app.services.avl_geometry_service import build_avl_geometry_file

        plane = self._make_plane_schema()
        config = SpacingConfig(auto_optimise=False, n_chord=12, n_span=12)
        avl_file = build_avl_geometry_file(plane, spacing_config=config)

        assert isinstance(avl_file, AvlGeometryFile)
        assert avl_file.title == "TestPlane"
        assert len(avl_file.surfaces) == 1

        content = repr(avl_file)
        assert "SURFACE" in content
        assert "Main Wing" in content
        assert "SECTION" in content
        assert "YDUPLICATE" in content

    def test_build_includes_control_surfaces(self):
        from app.services.avl_geometry_service import build_avl_geometry_file

        plane = self._make_plane_schema()
        config = SpacingConfig(auto_optimise=False)
        avl_file = build_avl_geometry_file(plane, spacing_config=config)

        content = repr(avl_file)
        assert "CONTROL" in content
        assert "aileron" in content

    def test_build_applies_mm_to_m_conversion(self):
        """When schema has metres, the output should also be in metres."""
        from app.services.avl_geometry_service import build_avl_geometry_file

        plane = self._make_plane_schema()
        config = SpacingConfig(auto_optimise=False)
        avl_file = build_avl_geometry_file(plane, spacing_config=config)

        # First section chord should be 0.2 (metres, passed through)
        assert avl_file.surfaces[0].sections[0].chord == 0.2
        # Reference chord should match
        assert abs(avl_file.reference.c_ref - 0.2) < 0.05  # approximate

    def test_build_with_auto_optimise_increases_nchord(self):
        from app.services.avl_geometry_service import build_avl_geometry_file

        plane = self._make_plane_schema()
        config = SpacingConfig(auto_optimise=True, n_chord=12)
        avl_file = build_avl_geometry_file(plane, spacing_config=config)

        # Wing has control surfaces → nchord should be ≥16
        assert avl_file.surfaces[0].n_chord >= 16

    def test_generate_avl_content_with_zero_cdcl(self):
        from app.services.avl_geometry_service import generate_avl_content_from_schema

        plane = self._make_plane_schema()
        config = SpacingConfig(auto_optimise=False)
        content = generate_avl_content_from_schema(plane, spacing_config=config)

        assert isinstance(content, str)
        assert "SURFACE" in content
        # In editor mode, CDCL should be all zeros
        assert "CDCL" in content
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator && poetry run pytest app/tests/test_avl_generator_integration.py -v`
Expected: FAIL — `ImportError: cannot import name 'build_avl_geometry_file'`

- [ ] **Step 3: Implement `build_avl_geometry_file` in avl_geometry_service.py**

Add these new functions to `app/services/avl_geometry_service.py`. The existing functions (`generate_avl_content`, `get_avl_geometry`, etc.) remain unchanged for now — we'll swap the implementation in a later step.

```python
# Add to app/services/avl_geometry_service.py (new functions)

from app.avl.geometry import (
    AvlAfile, AvlCdcl, AvlControl, AvlGeometryFile,
    AvlNaca, AvlReference, AvlSection, AvlSurface, AvlSymmetry,
)
from app.avl.spacing import optimise_surface_spacing
from app.schemas.aeroanalysisschema import SpacingConfig
from app.schemas.aeroplaneschema import AeroplaneSchema, AsbWingSchema, WingXSecSchema


def _build_airfoil_node(airfoil_ref: str):
    """Convert an airfoil reference string to the appropriate AVL airfoil type."""
    import os
    ref = str(airfoil_ref)
    name_lower = os.path.splitext(os.path.basename(ref))[0].lower() if ref else ""

    if name_lower.startswith("naca") and name_lower[4:].isdigit():
        return AvlNaca(name_lower[4:])

    from app.services.create_wing_configuration import _resolve_airfoil_reference
    resolved = _resolve_airfoil_reference(ref)
    if os.path.isfile(resolved):
        return AvlAfile(resolved)

    return AvlNaca("0012")


def _build_section(
    xsec: WingXSecSchema,
    controls: list[AvlControl],
) -> AvlSection:
    """Build an AvlSection from a WingXSecSchema."""
    airfoil = _build_airfoil_node(str(xsec.airfoil))

    import aerosandbox as asb
    asb_airfoil = asb.Airfoil(name=os.path.splitext(os.path.basename(str(xsec.airfoil)))[0])
    try:
        claf = 1.0 + 0.77 * asb_airfoil.max_thickness()
    except Exception:
        claf = 1.0

    return AvlSection(
        xyz_le=(xsec.xyz_le[0], xsec.xyz_le[1], xsec.xyz_le[2]),
        chord=xsec.chord,
        ainc=xsec.twist,
        airfoil=airfoil,
        claf=claf,
        cdcl=AvlCdcl.zeros(),
        controls=controls,
    )


def _build_controls_for_wing(wing: AsbWingSchema) -> list[list[AvlControl]]:
    """Build control surface commands for each section (matching ASB's pattern).

    ASB duplicates control commands to both the start and end section of each
    xsec that has a control surface. We replicate this.
    """
    from app.converters.model_schema_converters import _control_surface_for_xsec

    n = len(wing.x_secs)
    controls_per_section: list[list[AvlControl]] = [[] for _ in range(n)]

    for i, xsec in enumerate(wing.x_secs[:-1]):
        cs = _control_surface_for_xsec(xsec)
        if cs is None:
            continue
        xhinge = cs.hinge_point
        sgn_dup = 1.0 if cs.symmetric else -1.0
        ctrl = AvlControl(
            name=cs.name,
            gain=1.0,
            xhinge=xhinge,
            xyz_hvec=(0.0, 0.0, 0.0),
            sgn_dup=sgn_dup,
        )
        controls_per_section[i].append(ctrl)
        controls_per_section[i + 1].append(ctrl)

    return controls_per_section


def _build_surface(
    wing_name: str,
    wing: AsbWingSchema,
    spacing_config: SpacingConfig,
) -> AvlSurface:
    """Build an AvlSurface from a wing schema."""
    controls_per_section = _build_controls_for_wing(wing)

    sections = [
        _build_section(xsec, controls_per_section[i])
        for i, xsec in enumerate(wing.x_secs)
    ]

    surface = AvlSurface(
        name=wing_name,
        n_chord=spacing_config.n_chord,
        c_space=spacing_config.c_space,
        n_span=spacing_config.n_span,
        s_space=spacing_config.s_space,
        yduplicate=0.0 if wing.symmetric else None,
        sections=sections,
    )

    return optimise_surface_spacing(surface, spacing_config)


def build_avl_geometry_file(
    plane_schema: AeroplaneSchema,
    spacing_config: SpacingConfig | None = None,
) -> AvlGeometryFile:
    """Build a complete AvlGeometryFile from an AeroplaneSchema."""
    if spacing_config is None:
        spacing_config = SpacingConfig()

    import aerosandbox as asb
    from app.converters.model_schema_converters import aeroplane_schema_to_asb_airplane_async
    asb_airplane = aeroplane_schema_to_asb_airplane_async(plane_schema)

    xyz_ref = tuple(plane_schema.xyz_ref) if plane_schema.xyz_ref else (0.0, 0.0, 0.0)

    surfaces = []
    if plane_schema.wings:
        for wing_name, wing in plane_schema.wings.items():
            surfaces.append(_build_surface(wing_name, wing, spacing_config))

    return AvlGeometryFile(
        title=plane_schema.name,
        mach=0.0,
        symmetry=AvlSymmetry(iy_sym=0, iz_sym=0, z_sym=0.0),
        reference=AvlReference(
            s_ref=asb_airplane.s_ref,
            c_ref=asb_airplane.c_ref,
            b_ref=asb_airplane.b_ref,
            xyz_ref=xyz_ref,
        ),
        surfaces=surfaces,
    )


def generate_avl_content_from_schema(
    plane_schema: AeroplaneSchema,
    spacing_config: SpacingConfig | None = None,
) -> str:
    """Generate AVL file content string from schema (editor mode — zero CDCL)."""
    avl_file = build_avl_geometry_file(plane_schema, spacing_config)
    return repr(avl_file)
```

- [ ] **Step 4: Run tests to verify**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator && poetry run pytest app/tests/test_avl_generator_integration.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator
git add app/services/avl_geometry_service.py app/tests/test_avl_generator_integration.py
git commit -m "feat(gh-384): add AVL geometry builder — build_avl_geometry_file replaces asb.AVL.write_avl()"
```

---

## Task 7: Wire Up — Replace Old Generator and Inject CDCL at Analysis Time

**Files:**
- Modify: `app/services/avl_geometry_service.py` (swap `generate_avl_content`)
- Modify: `app/services/analysis_service.py` (inject CDCL)
- Modify: `app/api/utils.py` (pass configs)
- Modify: `app/tests/test_avl_generator_integration.py` (add wiring tests)

### 7.1 — Replace `generate_avl_content` to use new builder

- [ ] **Step 1: Write test for the swapped generate_avl_content**

```python
# Append to app/tests/test_avl_generator_integration.py

class TestGenerateAvlContentSwapped:
    """Tests that generate_avl_content (DB-based) now uses the new builder."""

    def test_generate_uses_new_builder(self, client_and_db):
        """Verify generate_avl_content produces output with our format markers."""
        from unittest.mock import patch, MagicMock
        from app.services.avl_geometry_service import generate_avl_content

        _, db = client_and_db

        mock_schema = MagicMock()
        mock_schema.name = "MockPlane"
        mock_schema.wings = None
        mock_schema.fuselages = None
        mock_schema.xyz_ref = [0, 0, 0]

        with patch("app.services.avl_geometry_service.get_aeroplane_schema_or_raise", return_value=mock_schema):
            content = generate_avl_content(db, "test-uuid")

        assert isinstance(content, str)
        assert "MockPlane" in content
        assert "SURFACE" not in content  # no wings → no surfaces
```

- [ ] **Step 2: Update `generate_avl_content` to use the new builder**

Replace the existing `generate_avl_content` function in `app/services/avl_geometry_service.py`:

```python
def generate_avl_content(db: Session, aeroplane_uuid) -> str:
    """Generate AVL geometry content from the current aeroplane state."""
    from app.services.analysis_service import get_aeroplane_schema_or_raise

    plane_schema = get_aeroplane_schema_or_raise(db, aeroplane_uuid)
    return generate_avl_content_from_schema(plane_schema)
```

Remove the old import of `aerosandbox`, `tempfile`, and `Path` from the function (the new builder handles everything internally).

- [ ] **Step 3: Run all existing tests to ensure no regressions**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator && poetry run pytest app/tests/test_avl_geometry.py app/tests/test_avl_generator_integration.py -v`
Expected: PASS

### 7.2 — Inject CDCL at analysis time

- [ ] **Step 4: Write test for CDCL injection**

```python
# Append to app/tests/test_avl_generator_integration.py

class TestCdclInjection:
    def test_inject_cdcl_replaces_zeros(self):
        from collections import OrderedDict
        from app.schemas.aeroplaneschema import AeroplaneSchema, AsbWingSchema, WingXSecSchema
        from app.schemas.aeroanalysisschema import CdclConfig, SpacingConfig, OperatingPointSchema
        from app.services.avl_geometry_service import build_avl_geometry_file
        from app.services.neuralfoil_cdcl_service import NeuralFoilCdclService

        plane = AeroplaneSchema(
            name="TestPlane",
            wings=OrderedDict({
                "Wing": AsbWingSchema(
                    name="Wing",
                    symmetric=True,
                    x_secs=[
                        WingXSecSchema(xyz_le=[0, 0, 0], chord=0.2, twist=0.0, airfoil="naca2412"),
                        WingXSecSchema(xyz_le=[0, 1.0, 0], chord=0.15, twist=0.0, airfoil="naca2412"),
                    ],
                ),
            }),
            xyz_ref=[0, 0, 0],
        )

        avl_file = build_avl_geometry_file(plane, SpacingConfig(auto_optimise=False))

        # Before injection: all CDCLs are zero
        for surf in avl_file.surfaces:
            for sec in surf.sections:
                assert sec.cdcl is not None
                assert sec.cdcl.is_zero()

        # Now inject
        from app.services.avl_geometry_service import inject_cdcl
        op = OperatingPointSchema(velocity=30.0, altitude=0.0)
        config = CdclConfig()
        inject_cdcl(avl_file, plane, op, config)

        # After injection: CDCLs should have non-zero values
        for surf in avl_file.surfaces:
            for sec in surf.sections:
                assert sec.cdcl is not None
                assert not sec.cdcl.is_zero()
                assert sec.cdcl.cd_0 > 0
```

- [ ] **Step 5: Implement `inject_cdcl` function**

Add to `app/services/avl_geometry_service.py`:

```python
def inject_cdcl(
    avl_file: AvlGeometryFile,
    plane_schema: AeroplaneSchema,
    operating_point: "OperatingPointSchema",
    cdcl_config: "CdclConfig",
) -> None:
    """Inject NeuralFoil CDCL values into an AvlGeometryFile in-place.

    Replaces zero CDCLs with computed values. Non-zero CDCLs (user-edited) are preserved.
    """
    from app.schemas.aeroanalysisschema import CdclConfig
    from app.services.neuralfoil_cdcl_service import NeuralFoilCdclService, compute_reynolds_number

    service = NeuralFoilCdclService()

    wing_list = list(plane_schema.wings.values()) if plane_schema.wings else []

    for surf_idx, surface in enumerate(avl_file.surfaces):
        if surf_idx >= len(wing_list):
            break
        wing = wing_list[surf_idx]

        for sec_idx, section in enumerate(surface.sections):
            if section.cdcl is not None and not section.cdcl.is_zero():
                continue

            if sec_idx >= len(wing.x_secs):
                continue
            xsec = wing.x_secs[sec_idx]

            re = compute_reynolds_number(
                velocity=operating_point.velocity if isinstance(operating_point.velocity, float) else operating_point.velocity,
                chord=xsec.chord,
                altitude=operating_point.altitude,
            )

            import aerosandbox as asb
            from app.converters.model_schema_converters import _build_asb_airfoil
            airfoil = _build_asb_airfoil(xsec.airfoil)

            section.cdcl = service.compute_cdcl(
                airfoil=airfoil,
                re=re,
                mach=avl_file.mach,
                config=cdcl_config,
            )
```

- [ ] **Step 6: Run CDCL injection test**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator && poetry run pytest app/tests/test_avl_generator_integration.py::TestCdclInjection -v`
Expected: PASS

### 7.3 — Wire into analysis_service.py

- [ ] **Step 7: Update analysis flow in analysis_service.py**

In `app/services/analysis_service.py`, update the function that calls `analyse_aerodynamics` for AVL (around line 329). The new flow:

1. If user has saved AVL content and it has non-zero CDCLs → use as-is (existing behavior)
2. If user has saved AVL content but CDCLs are all zeros → inject NeuralFoil CDCL into the string
3. If no user content → build via `build_avl_geometry_file`, inject CDCL, use `repr()`

Replace the relevant section where `user_avl_content` is fetched:

```python
    user_avl_content = None
    if analysis_tool == AnalysisToolUrlType.AVL:
        from app.services.avl_geometry_service import (
            get_user_avl_content,
            build_avl_geometry_file,
            inject_cdcl,
            generate_avl_content_from_schema,
        )
        from app.schemas.aeroanalysisschema import CdclConfig, SpacingConfig

        user_avl_content = get_user_avl_content(db, aeroplane_uuid)
        if user_avl_content is None:
            cdcl_config = operating_point.cdcl_config or CdclConfig()
            spacing_config = operating_point.spacing_config or SpacingConfig()
            avl_file = build_avl_geometry_file(plane_schema, spacing_config)
            inject_cdcl(avl_file, plane_schema, operating_point, cdcl_config)
            user_avl_content = repr(avl_file)
```

Apply the same pattern to the strip forces analysis function (around line 1418).

- [ ] **Step 8: Run all tests**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator && poetry run pytest -x -q --tb=short -m "not slow" --deselect app/tests/test_ehawk_designer_workflow_integration.py::test_ehawk_designer_workflow_stepwise --deselect app/tests/test_ehawk_wing_rest_workflow_integration.py::test_rest_wing_vase_mode_step_export_workflow_via_wingconfig`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator
git add app/services/avl_geometry_service.py app/services/analysis_service.py app/api/utils.py app/tests/test_avl_generator_integration.py
git commit -m "feat(gh-384): wire new AVL generator into analysis flow with CDCL injection"
```

---

## Task 8: User-Edited CDCL Preservation and Edge Cases

**Files:**
- Modify: `app/tests/test_avl_generator_integration.py`
- Modify: `app/services/avl_geometry_service.py` (if needed)

### 8.1 — Test user-edited CDCL preservation

- [ ] **Step 1: Write tests**

```python
# Append to app/tests/test_avl_generator_integration.py

class TestUserEditedCdclPreservation:
    def test_nonzero_cdcl_is_preserved(self):
        from app.avl.geometry import AvlCdcl, AvlGeometryFile, AvlSection, AvlSurface, AvlSymmetry, AvlReference
        from app.schemas.aeroanalysisschema import CdclConfig, OperatingPointSchema
        from app.services.avl_geometry_service import inject_cdcl
        from collections import OrderedDict
        from app.schemas.aeroplaneschema import AeroplaneSchema, AsbWingSchema, WingXSecSchema

        user_cdcl = AvlCdcl(cl_min=-0.5, cd_min=0.02, cl_0=0.1, cd_0=0.009, cl_max=1.2, cd_max=0.04)

        avl_file = AvlGeometryFile(
            title="Test",
            mach=0.0,
            symmetry=AvlSymmetry(),
            reference=AvlReference(s_ref=1.0, c_ref=0.2, b_ref=2.0, xyz_ref=(0, 0, 0)),
            surfaces=[
                AvlSurface(
                    name="Wing", n_chord=12, c_space=1.0,
                    sections=[
                        AvlSection(xyz_le=(0, 0, 0), chord=0.2, cdcl=user_cdcl),
                        AvlSection(xyz_le=(0, 1, 0), chord=0.15, cdcl=AvlCdcl.zeros()),
                    ],
                ),
            ],
        )

        plane = AeroplaneSchema(
            name="Test",
            wings=OrderedDict({"Wing": AsbWingSchema(
                name="Wing", symmetric=True,
                x_secs=[
                    WingXSecSchema(xyz_le=[0, 0, 0], chord=0.2, twist=0.0, airfoil="naca2412"),
                    WingXSecSchema(xyz_le=[0, 1, 0], chord=0.15, twist=0.0, airfoil="naca2412"),
                ],
            )}),
            xyz_ref=[0, 0, 0],
        )

        op = OperatingPointSchema(velocity=30.0, altitude=0.0)
        inject_cdcl(avl_file, plane, op, CdclConfig())

        # First section: user-edited, should be preserved
        assert avl_file.surfaces[0].sections[0].cdcl == user_cdcl
        # Second section: was zero, should be replaced
        assert not avl_file.surfaces[0].sections[1].cdcl.is_zero()
```

- [ ] **Step 2: Run test**

Run: `cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator && poetry run pytest app/tests/test_avl_generator_integration.py::TestUserEditedCdclPreservation -v`
Expected: PASS (the inject_cdcl function already checks `is_zero()` before replacing)

- [ ] **Step 3: Commit**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator
git add app/tests/test_avl_generator_integration.py
git commit -m "test(gh-384): add user-edited CDCL preservation test"
```

---

## Task 9: Final Verification — Full Test Suite and Coverage

**Files:** No new files — verification only.

- [ ] **Step 1: Run full test suite (excluding known failures)**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator
poetry run pytest -q --tb=short -m "not slow" \
  --deselect app/tests/test_ehawk_designer_workflow_integration.py::test_ehawk_designer_workflow_stepwise \
  --deselect app/tests/test_ehawk_wing_rest_workflow_integration.py::test_rest_wing_vase_mode_step_export_workflow_via_wingconfig
```

Expected: ALL PASS

- [ ] **Step 2: Check test coverage for new modules**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator
poetry run pytest --cov=app/avl --cov=app/services/neuralfoil_cdcl_service --cov-report=term-missing \
  app/tests/test_avl_dataclasses.py \
  app/tests/test_neuralfoil_cdcl_service.py \
  app/tests/test_avl_spacing.py \
  app/tests/test_avl_generator_integration.py
```

Expected: >80% coverage for `app/avl/` and `app/services/neuralfoil_cdcl_service.py`

- [ ] **Step 3: Lint check**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator
poetry run ruff check app/avl/ app/services/neuralfoil_cdcl_service.py
poetry run ruff format --check app/avl/ app/services/neuralfoil_cdcl_service.py
```

Expected: No errors

- [ ] **Step 4: Final commit if any lint fixes needed, then push**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.worktrees/feat/gh-384-avl-generator
git push github feat/gh-384-avl-generator
```
