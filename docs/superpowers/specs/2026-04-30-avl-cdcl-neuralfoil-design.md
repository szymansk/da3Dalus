# AVL Own Generator, CDCL via NeuralFoil & Intelligent Spacing

## Problem

1. **No profile drag:** AVL analyses compute only induced drag (CDi).
   CDCL blocks are all zeros — no friction, pressure, or separation
   drag. This inflates L/D ratios and produces unrealistic drag polars.

2. **Suboptimal panel distribution:** Aerosandbox's `write_avl()` uses
   fixed defaults (Nchord=12, Nspan=12, cosine everywhere). It does
   not adapt spacing to geometry features like control surface
   boundaries, taper breaks, or sweep — leaving accuracy on the table.

## Solution Overview

1. **Own AVL file generator** — replace `asb.AVL.write_avl()` with a
   self-serialising dataclass hierarchy where each component implements
   `__repr__` to emit its AVL format block.
2. **NeuralFoil CDCL computation** — at analysis time, compute
   per-section profile drag polars from NeuralFoil based on actual
   flight conditions (velocity, altitude, chord → Reynolds number).
3. **3-point CDCL fit** — extract CL_min (with CD), CD_min (with CL),
   CL_max (with CD) from the NeuralFoil polar to populate the AVL
   CDCL format.
4. **Intelligent spacing** — automatically adapt panel counts and
   spacing distributions based on geometry features (control surfaces,
   taper breaks, sweep, aligned surfaces).

## Data Structure: `AvlGeometryFile`

A self-serialising dataclass tree. `repr(avl_file)` produces a
complete `.avl` file string.

```
AvlGeometryFile
├── title: str
├── mach: float
├── symmetry: AvlSymmetry
│   ├── iy_sym: int (0, 1, -1)
│   ├── iz_sym: int (0, 1, -1)
│   └── z_sym: float
├── reference: AvlReference
│   ├── s_ref: float
│   ├── c_ref: float
│   ├── b_ref: float
│   └── xyz_ref: tuple[float, float, float]
├── cdp: float = 0.0
├── surfaces: list[AvlSurface]
│   ├── name: str
│   ├── n_chord: int
│   ├── c_space: float
│   ├── n_span: int | None
│   ├── s_space: float | None
│   ├── yduplicate: float | None
│   ├── component: int | None
│   ├── scale: tuple[float, float, float] | None
│   ├── translate: tuple[float, float, float] | None
│   ├── angle: float | None
│   ├── nowake: bool = False
│   ├── noalbe: bool = False
│   ├── noload: bool = False
│   ├── cdcl: AvlCdcl | None
│   └── sections: list[AvlSection]
│       ├── xyz_le: tuple[float, float, float]
│       ├── chord: float
│       ├── ainc: float = 0.0
│       ├── n_span: int | None
│       ├── s_space: float | None
│       ├── airfoil: AvlNaca | AvlAirfoilInline | AvlAfile | None
│       ├── claf: float | None
│       ├── cdcl: AvlCdcl | None
│       ├── controls: list[AvlControl]
│       └── designs: list[AvlDesign]
└── bodies: list[AvlBody]
    ├── name: str
    ├── n_body: int
    ├── b_space: float
    ├── yduplicate: float | None
    ├── scale: tuple[float, float, float] | None
    ├── translate: tuple[float, float, float] | None
    └── bfile: str
```

### Key sub-structures

```python
@dataclass
class AvlCdcl:
    cl_min: float     # CL1 — negative stall boundary
    cd_min: float     # CD1
    cl_0: float       # CL2 — drag minimum CL
    cd_0: float       # CD2 — minimum drag coefficient
    cl_max: float     # CL3 — positive stall boundary
    cd_max: float     # CD3

@dataclass
class AvlControl:
    name: str
    gain: float
    xhinge: float
    xyz_hvec: tuple[float, float, float]
    sgn_dup: float
```

Each class implements `__repr__` returning its AVL text block.
`repr(AvlGeometryFile(...))` produces the complete file content.

### Module location

`app/avl/geometry.py` — pure data structures, no DB dependency.

## NeuralFoil CDCL Service

New service: `app/services/neuralfoil_cdcl_service.py`

```python
class NeuralFoilCdclService:
    def compute_cdcl(
        self,
        airfoil: asb.Airfoil,
        re: float,
        mach: float,
        config: CdclConfig,
    ) -> AvlCdcl:
        """Run NeuralFoil, extract 3-point CDCL fit."""

    @lru_cache
    def _get_polar(
        self, airfoil_name: str, re: float, mach: float, ...
    ) -> dict:
        """Cached NeuralFoil call — same airfoil+Re reuses result."""
```

### CDCL 3-point fitting algorithm

1. Run NeuralFoil over alpha range → get CL[] and CD[] arrays
2. **Point 2 (CL2, CD2):** find the alpha where CD is minimal →
   that CL and CD become the drag bucket bottom
3. **Point 3 (CL3, CD3):** find CL_max from NeuralFoil → use that
   CL and its corresponding CD as the positive stall point
4. **Point 1 (CL1, CD1):** find CL_min from NeuralFoil → use that
   CL and its corresponding CD as the negative stall point

### Reynolds number per section

```python
re = velocity * chord / kinematic_viscosity(altitude)
```

Velocity and altitude come from the `OperatingPoint`. Chord is known
per section. Kinematic viscosity is computed from
`asb.Atmosphere(altitude=...).kinematic_viscosity()`.

### In-memory cache

`@lru_cache` keyed on `(airfoil_name, re, mach, n_crit)`. Same
airfoil at same Re reuses the NeuralFoil result. Cache lives for the
duration of one analysis request.

## CdclConfig Schema

```python
class CdclConfig(BaseModel):
    alpha_start_deg: float = -10.0
    alpha_end_deg: float = 16.0
    alpha_step_deg: float = 1.0
    model_size: str = "large"
    n_crit: float = 9.0
    xtr_upper: float = 1.0
    xtr_lower: float = 1.0
    include_360_deg_effects: bool = False
```

Added as an optional field to `OperatingPointSchema` (or the analysis
request). When omitted, defaults apply.

## Integration Flow

### Analysis path (CDCL computed dynamically)

```
analyze_wing/airplane(operating_point)
  → avl_content = get_user_avl_content()
  → if avl_content:
      → check CDCL values: all zeros?
        → yes: compute via NeuralFoil, replace in string
        → no: respect user-edited values
  → else:
      → build AvlGeometryFile from aeroplane schema
      → compute CDCL per section via NeuralFoilCdclService
      → avl_content = repr(avl_file)
  → run AVL with avl_content
```

### Geometry editor path (no CDCL)

```
generate_avl_content()
  → build AvlGeometryFile from aeroplane schema
  → CDCL = AvlCdcl(0, 0, 0, 0, 0, 0) with comment:
    "! Profile drag is computed dynamically at analysis time via NeuralFoil"
  → return repr(avl_file)
```

## Unit handling

AVL requires all lengths in a consistent unit ("Lunit"). In da3Dalus,
the AVL file uses **metres**. The topology/schema layer uses **mm**.

| AVL field | Unit in file | Source unit | Conversion |
|-----------|-------------|-------------|------------|
| Sref | m² | mm² | ×0.000001 |
| Cref, Bref | m | mm | ×0.001 |
| Xref, Yref, Zref | m | mm | ×0.001 |
| Xle, Yle, Zle | m | mm | ×0.001 |
| Chord | m | mm | ×0.001 |
| Ainc | degrees | degrees | none |
| Mach | dimensionless | — | none |
| CDCL (CL, CD) | dimensionless | — | none |
| CLAF | dimensionless | — | none |
| CONTROL Xhinge | x/c (0–1) | x/c (0–1) | none |
| CONTROL XYZhvec | direction vector | — | none |

The generator must apply mm→m conversion for all geometry lengths.
This is currently handled by the converters (`scale=0.001`); the new
generator inherits this responsibility.

**Sref scales quadratically** (mm²→m² = ×10⁻⁶), all other lengths
scale linearly (×10⁻³). This is the most common source of unit bugs.

## What replaces `asb.AVL.write_avl()`

The new `AvlGeometryFile` replaces the Aerosandbox file writer. The
converter (`model_schema_converters.py`) builds `AvlSection` objects
instead of `asb.WingXSec` objects for the geometry file path.

Aerosandbox is still used for:
- Running AVL (the `asb.AVL` solver)
- `asb.Airfoil` objects (coordinates, NeuralFoil calls, thickness)
- `asb.Atmosphere` (kinematic viscosity, temperature)
- `asb.OperatingPoint` (flight conditions for the solver)

Only file generation is decoupled.

## Intelligent Spacing Optimisation

The own generator can apply AVL's 4 spacing rules automatically
(avl_doc.txt, lines 1086–1131) instead of relying on fixed defaults.

### Spacing distributions (Cspace, Sspace)

| Value | Distribution | When to use |
|-------|-------------|-------------|
| 1.0 | cosine | **Default** — bunched at both ends |
| 2.0 | sine | Bunched at start of segment |
| -2.0 | -sine | Root-to-tip on unswept wings without centreline chord break |
| 3.0 | equal | Rarely useful, slow convergence |

Intermediate values (e.g. 1.5) produce blended distributions.

### Automatic optimisations

The generator inspects the geometry and sets spacing intelligently:

1. **Control surface detection:** if any section has CONTROL entries,
   increase `n_chord` (e.g. 12→16) to resolve the camberline
   discontinuity at the hinge line (Rule 3).

2. **Unswept wing detection:** if the wing has no significant sweep
   and no centreline chord break, use `-sine` (-2.0) spanwise spacing
   from root to tip. This is equivalent to cosine across the full
   span and more efficient (avl_doc.txt, line 1040–1047).

3. **Aligned surface consistency (Rule 1):** if two surfaces share
   similar y,z coordinates (e.g. wing + horizontal tail), enforce
   identical spanwise spacing to prevent trailing vortices from
   passing through downstream control points.

4. **Local span refinement:** at control surface boundaries (flap/
   aileron start/end), use per-section `n_span` with tighter spacing
   instead of uniform distribution across the whole surface.

5. **Bidirectional refinement (Rule 4):** when the user requests
   higher resolution, scale both `n_chord` and `n_span` together —
   never just one direction.

### SpacingConfig schema

```python
class SpacingConfig(BaseModel):
    n_chord: int = 12
    c_space: float = 1.0       # cosine default
    n_span: int = 20
    s_space: float = 1.0       # cosine default
    auto_optimise: bool = True  # apply intelligent rules above
```

When `auto_optimise=True` (default), the generator overrides the
base values where geometry features warrant it. When `False`, the
base values are used as-is, giving the user full manual control.

### Refinement study reference (avl_doc.txt, lines 1058–1081)

| Spacing | Nchord×Nspan | Oswald error |
|---------|-------------|-------------|
| Cosine | 1×4 | +0.09% |
| Uniform | 1×4 | +13.45% |
| Cosine | 4×16 | -0.00% |
| Uniform | 8×32 | +1.54% |

Cosine spacing at 2×8 is more accurate than uniform at 8×32.

## Files affected

| File | Change |
|------|--------|
| `app/avl/geometry.py` | **New** — dataclass hierarchy |
| `app/services/neuralfoil_cdcl_service.py` | **New** — CDCL fitting |
| `app/schemas/aeroanalysisschema.py` | Add `CdclConfig` to request |
| `app/services/avl_geometry_service.py` | Use `AvlGeometryFile` instead of `asb.AVL.write_avl()` |
| `app/services/analysis_service.py` | CDCL injection in analysis flow |
| `app/converters/model_schema_converters.py` | Build `AvlSection` for file generation |
| `app/api/utils.py` | Pass CDCL + spacing config through |

## Acceptance Criteria

### AVL file generator
- [ ] New `AvlGeometryFile` dataclass produces valid `.avl` files
      (verified against Aerosandbox output for existing test cases)
- [ ] Each dataclass component serialises correctly via `__repr__`

### CDCL / NeuralFoil
- [ ] Each section in analysed `.avl` files has CDCL values from
      NeuralFoil (not zeros)
- [ ] Reynolds number computed per section from velocity, chord,
      altitude
- [ ] User-edited CDCL values (non-zero) are preserved during analysis
- [ ] Geometry editor shows zeros with explanatory comment
- [ ] `CdclConfig` is configurable via request, with sensible defaults
- [ ] In-memory cache prevents redundant NeuralFoil calls for same
      airfoil+Re
- [ ] AVL total drag output includes induced + profile drag

### Intelligent spacing
- [ ] `auto_optimise=True` increases Nchord when control surfaces
      are present
- [ ] Unswept wings without centreline break use -sine spanwise
      spacing
- [ ] Aligned surfaces (same y,z) get identical spanwise spacing
- [ ] `SpacingConfig` is configurable with sensible defaults
- [ ] `auto_optimise=False` uses base values without modification

### Unit handling
- [ ] All geometry lengths (Sref, Cref, Bref, XYZref, Xle/Yle/Zle,
      Chord) are converted from mm to metres
- [ ] Sref is converted mm²→m² (×10⁻⁶, quadratic scaling)
- [ ] Dimensionless values (CDCL, CLAF, Mach, Xhinge) are passed
      through without conversion
- [ ] Unit conversion is tested with known geometry

### Testing
- [ ] Existing tests pass
- [ ] New tests cover: dataclass serialisation, CDCL fitting, cache
      behaviour, user-edit preservation, spacing optimisation rules,
      unit conversion
- [ ] Test coverage >80%

## Out of Scope

- ANTLR grammar / formal AVL parser
- Monaco syntax highlighting changes
- AVL `.mass` or `.run` file generation
- Database caching of NeuralFoil polars
- CDCL for BODY elements (AVL does not support this)
