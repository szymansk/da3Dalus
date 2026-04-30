# AVL CDCL Integration via NeuralFoil

## Problem

AVL analyses currently compute only **induced drag** (CDi) from the
Trefftz plane. The CDCL blocks in generated `.avl` files are all zeros
(`0 0 0 0 0 0`), meaning no profile drag (friction, pressure,
separation) is accounted for. This leads to:

- Overly optimistic total drag predictions
- Inflated L/D ratios
- Unrealistic drag polars

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

## Files affected

| File | Change |
|------|--------|
| `app/avl/geometry.py` | **New** — dataclass hierarchy |
| `app/services/neuralfoil_cdcl_service.py` | **New** — CDCL fitting |
| `app/schemas/aeroanalysisschema.py` | Add `CdclConfig` to request |
| `app/services/avl_geometry_service.py` | Use `AvlGeometryFile` instead of `asb.AVL.write_avl()` |
| `app/services/analysis_service.py` | CDCL injection in analysis flow |
| `app/converters/model_schema_converters.py` | Build `AvlSection` for file generation |
| `app/api/utils.py` | Pass CDCL config through |

## Acceptance Criteria

- [ ] New `AvlGeometryFile` dataclass produces valid `.avl` files
      (verified against Aerosandbox output for existing test cases)
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
- [ ] Existing tests pass
- [ ] New tests cover: dataclass serialisation, CDCL fitting, cache
      behaviour, user-edit preservation
- [ ] Test coverage >80%

## Out of Scope

- ANTLR grammar / formal AVL parser
- Monaco syntax highlighting changes
- AVL `.mass` or `.run` file generation
- Database caching of NeuralFoil polars
- CDCL for BODY elements (AVL does not support this)
