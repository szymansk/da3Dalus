# wingconfiguration-coordinate-system — Technical Design

> Use-case design, nested under the module
> [`cad-designer-topology`](../design.md).
> Focuses on HOW this use case is built, derived from the legacy code.
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Library API in full: [`../contracts.md`](../contracts.md) §4–§7.
> Sibling slices: [`../creator-execution-model/`](../creator-execution-model/design.md),
> [`../json-polymorphic-roundtrip/`](../json-polymorphic-roundtrip/design.md).
>
> ⚠ **Entirely inside the FROZEN layer (ADR 0002).** Several behaviours below are
> defects that are deliberately preserved.

## Interface

### Domain literal types — `cad_designer/airplane/types.py` (38 l.) 🟢

| Name | Definition | Validator |
|---|---|---|
| `Factor` | `confloat(ge=0, le=1.0)` | pydantic bounds |
| `DihedralInDegrees` | `confloat(ge=-180.0, le=180.0)` | pydantic bounds |
| `CoordinateSystemBase` | `Annotated[Literal["world","wing","root_airfoil","tip_airfoil"], Field(...), BeforeValidator(.lower())]` | case-folding |
| `WingSegmentType` | `Annotated[Literal["root","segment","tip"], …, BeforeValidator(.lower())]` | case-folding |
| `TipType` | `Annotated[Literal["flat","round"], …, BeforeValidator(.lower())]` | case-folding |
| `WingSides` | `Annotated[Literal["LEFT","RIGHT","BOTH"], …, BeforeValidator(.upper())]` | **upper**-casing |
| `ShapeId` | `NewType("ShapeId", str)` | none — documents "a reference to an upstream shape key" |
| `CreatorId` | `NewType("CreatorId", str)` | none — documents "unique identifier for a construction step" |

Every `BeforeValidator` is guarded with `if isinstance(x, str)`, so a non-string
passes through and fails at the `Literal` check instead. 🟢 The `Field(...)`
descriptions on these aliases are what surface as parameter documentation in the
Creator Catalog. 🟡

### `CoordinateSystem` — `aircraft_topology/wing/CoordinateSystem.py` (145 l.) 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `__init__` | `(xDir, yDir, zDir, origin: tuple[float,float,float] \| list[float])` | — | stores all four as **lists**; derives `euler_xyz` (l.48-53) |
| `__getstate__` | `()` | `dict` | `xDir`, `yDir`, `zDir`, `origin`, **`euler_xyz`** (l.55-63) |
| `from_json_dict` | `(data: dict)` → `CoordinateSystem` | `@staticmethod` | defaults to the identity basis; **ignores** a serialised `euler_xyz` (l.101-117) |
| `from_json` / `save_to_json` | `(file_path: str)` | — | single-object file I/O (l.119-144) |
| `_is_valid_rotation_matrix` | `(R)` | `bool` | `classmethod`; shape, orthonormality and determinant (l.65-80) |
| `_rotation_matrix_to_euler_angles` | `(R_matrix, order='XYZ')` | `ndarray` | `classmethod`; validates then decomposes (l.82-99) |
| `InvalidRotationMatrixException` | — | — | raised by the above |
| `InvalidRotationOrderException` | — | — | 🔴 declared (l.7), never raised |

The class docstring states its role precisely: each `Airfoil` has a
`CoordinateSystem` defining its position and orientation, and the parameters of
`Airfoil`s and `WingSegment`s (length, dihedral, incidence, relative rotation
point, sweep) are used to compute the transforms between them — **each system is
defined relative to the previous one in the chain**. 🟢

### `WingConfiguration` — the parts owned by this slice 🟢

| Symbol | Purpose |
|---|---|
| `_set_standard_spare_origin_vector(segment_number, spare)` | resolve a spar's vector and origin; contains the frozen dead branch (l.354-372) |
| `_get_standard_spare_origin_and_vector(start_segment, end_segment, spare_position_factor)` | returns a 4-tuple `(vector, origin, …, …)` centred on the camber line |
| `get_wing_workplane(segment=0, ignore_nose_point=False)` | build and cache the segment's CadQuery `Workplane` (l.374-400) |
| `_get_absolute_segment_coordinate_system` / `_get_relative_segment_coordinate_system` | the two parameterisations selected by `self.parameters` |

The full field-by-field constructor is tabled in
[`wing-design`](../../wing-design/design.md); the spar **solver** and section
geometry are that module's too. 🟢

### Component placement classes 🟢

| Class | Constructor | Note |
|---|---|---|
| `Position` | `(x, y, z)` + `get_x/y/z` | plain value object |
| `ComponentInformation` | `(height, width, length: PositiveFloat, rot_x/rot_y/rot_z: float = 0.0, trans_x/trans_y/trans_z: float = 0.0)` | `get_corner_point()`, `get_middle_point()`, `get_z_axis()` |
| `ServoInformation(ComponentInformation)` | `(height, width, length, lever_length: NonNegativeFloat, rot_*, trans_*, servo: Servo \| None = None)` | dimensions are read-only properties backed by `self.servo`; precomputes eight `_corner_vecs` |
| `EngineInformation(ComponentInformation)` | `(down_thrust, side_thrust, position: Position, length, width, height, screw_hole_circle, mount_box_length, screw_din_diameter, screw_length, rot_x = 0.0)` | maps `down_thrust → rot_y`, `side_thrust → rot_z` |
| `Printer3dSettings` | `(layer_height = 0.24, wall_thickness = 0.42, rel_gap_wall_thickness = 0.075)` | millimetres |

### `AirplaneConfiguration` 🟢

| Symbol | Signature | Note |
|---|---|---|
| `__init__` | `(name: str, total_mass_kg: float, wings: list[WingConfiguration], fuselages: list[FuselageConfiguration] \| None = None)` | sets `total_mass`, `_main_wing_index = 0`, `_main_wing = wings[0]` |
| `to_dict` | `()` → `dict` | `"fuselages"` present only when truthy |
| `save_to_json` / `save_to_zip` | `(path)` | `indent=4`; the zip builds a temp `wings/` + `fuselages/` tree |
| `asb_airplane` | `cached_property` → `asb.Airplane` | `mm_to_m_scale = 1.0e-3`; `xyz_ref=None`; AVL `profile_drag_coefficient = 0.0`; assigns `_asb_main_wing` 🟡 |
| `airplane_analysis` | `(CG_percent_MAC_in_front_of_NP=12.5, elevation_m=0, rho_kgm3=1.225, gravity=9.81)` | α sweep over `linspace(-20, 20, 300)` |

### CadQuery extensions and decorators 🟢

| Symbol | Purpose |
|---|---|
| `cq_plugins/__init__.py` | imports `fix_shape`, `segmentToEdge`, `display`, `offest3D`, `sew_fix_shape`, `wing` — installing the monkey-patches |
| `conditional_execute(env_var_name)` | gate a `Workplane` method on an env var; returns `self` when disabled |
| `fluent_init(cls)` | attach a static `.init()` factory whose signature omits `self` |

## Main Flow

### F1 — Constructing a coordinate system 🟢

```
CoordinateSystem(xDir, yDir, zDir, origin):

  self.xDir/yDir/zDir/origin = list(...)                       # tuples normalised to lists
  R = np.matrix([xDir, yDir, zDir]).T                          # rows → columns
  self.euler_xyz = _rotation_matrix_to_euler_angles(R, 'XYZ').tolist()

_rotation_matrix_to_euler_angles(R, order='XYZ'):
  if not _is_valid_rotation_matrix(R):
      raise InvalidRotationMatrixException("The provided matrix is not a valid rotation matrix.")
  return Rotation.from_matrix(R).as_euler(order.lower(), degrees=True)

_is_valid_rotation_matrix(R):
  R.shape == (3, 3)
  and np.allclose(R @ R.T, np.identity(3), atol=1e-6)      # orthonormal
  and np.isclose(np.linalg.det(R), 1.0,   atol=1e-6)       # right-handed
```

Two things follow. First, the transpose matters: the three direction vectors are
supplied as **rows** and become the matrix **columns**, which is what makes
`R @ R.T ≈ I` the orthonormality test. Second, `as_euler(order.lower(), …)`
converts the caller's `'XYZ'` into `'xyz'` — **extrinsic** in SciPy's convention.
🟡 A consumer expecting intrinsic XYZ angles would read a different rotation for
any non-commuting combination.

### F2 — Loading a coordinate system 🟢

```
from_json_dict(data):
  return CoordinateSystem(
      xDir  = data.get('xDir',   [1, 0, 0]),
      yDir  = data.get('yDir',   [0, 1, 0]),
      zDir  = data.get('zDir',   [0, 0, 1]),
      origin= data.get('origin', [0, 0, 0]),
  )
```

`euler_xyz` is **emitted** by `__getstate__` but never read back — it is
recomputed by the constructor. A hand-edited value is silently discarded, and a
serialised frame that was somehow invalid raises on load rather than on save. 🟢

### F3 — Resolving a spar's origin and vector 🟢

```
_set_standard_spare_origin_vector(segment_number, spare):        # l.354-372

  if spare.spare_position_factor is None:
      spare.spare_position_factor = 0.25                    # ← the quarter-chord default

  if spare.spare_vector is None and spare.spare_position_factor is not None:
      spare.spare_vector, _, _, _ = self._get_standard_spare_origin_and_vector(
          start_segment=segment_number, end_segment=segment_number,
          spare_position_factor=spare.spare_position_factor)
      # "make spare vector following the spare_position_factor,
      #  centered inside of the airfoil at the camber (middle of surfaces)"

  elif spare.spare_vector is None:                          # ← UNREACHABLE (BR-CT27)
      spare.spare_vector = self.get_wing_workplane(segment_number).plane.yDir

  else:
      spare.spare_vector = spare.spare_vector.normalized()

  if spare.spare_origin is None:                            # independent of the branch above
      _, spare.spare_origin, _, _ = self._get_standard_spare_origin_and_vector(...)
```

The `elif` is dead because the preceding `if` already covers
`spare_vector is None` — the `spare_position_factor is not None` conjunct is
always true after the default is applied. Preserved deliberately (ADR 0002).

The immediately preceding method (l.348-352) is the **follow-mode** counterpart,
which chains a spar's origin off the previous segment's:

```
spare.spare_origin = (prev.spare_list[spare_idx].spare_origin
                      + prev.spare_list[spare_idx].spare_vector * prev.length)
```

The *consumers* of this resolution — `should_preserve_normal_spare` and
`_recompute_spare_vectors`, which decide when the app is allowed to overwrite a
solver-produced spar — belong to
[`wing-design`](../../wing-design/design.md) §F5. 🟢

### F4 — Building a segment workplane 🟢

```
get_wing_workplane(segment=0, ignore_nose_point=False):           # l.374-400

  if   self.parameters == "aerosandbox":
      all_trans = self._get_absolute_segment_coordinate_system(segment, ignore_nose_point)
  elif self.parameters == "relative":
      all_trans = self._get_relative_segment_coordinate_system(segment, ignore_nose_point)
  else:
      raise ValueError(f"Unknown parameter type {self.parameters}, "
                       f"should be 'absolute' or 'relative'")     # 🟡 names a dead value

  normal = all_trans.transpose()[2]
  origin = all_trans.transpose()[3]
  xdir   = all_trans.transpose()[0]
  plane  = Plane(origin=origin.tolist()[:3], xDir=xdir.tolist()[:3],
                 normal=normal.tolist()[:3])
```

The transform is a 4×4 homogeneous matrix: transposing exposes column 0 as the
local x direction, column 2 as the normal (local z) and column 3 as the
translation. Each is truncated to its first three components. The docstring
records that the result is **cached for performance**. 🟢

### F5 — Placing a component 🟢

```
get_corner_point() -> gp_Pnt(trans_x, trans_y, trans_z)

get_middle_point() -> gp_Vec:
    middle = gp_Vec(trans_x + length/2,
                    trans_y - width/2,
                    trans_z - length/2)          # ← 🟡 known frozen bug, deliberately unfixed (ADR 0002): length, where height reads as intended
    middle.Rotate(gp_Ax1(get_corner_point(), gp_DX), rot_x)
    middle.Rotate(gp_Ax1(get_corner_point(), gp_DY), rot_y)
    middle.Rotate(gp_Ax1(get_corner_point(), gp_DZ), rot_z)
    return middle

get_z_axis() -> gp_Dir:
    z = gp_DZ                                    # ← 🟢 aliasing fixed (Q-CT-2); was an ALIAS of the module singleton
    z.Rotate(gp_Ax1(get_corner_point(), gp_DX), rot_x)
    z.Rotate(gp_Ax1(get_corner_point(), gp_DY), rot_y)
    z.Rotate(gp_Ax1(get_corner_point(), gp_DZ), rot_z)
    return z
```

Rotation order is **X → Y → Z**, always about the corner point (not the centre).
`gp_Vec.Rotate` mutates the receiver, which is fine for the local `middle`; but
`gp_Dir.Rotate` mutating `gp_DZ` — a module-level singleton — corrupts it for
the whole process, and the axes `gp_DX`/`gp_DY` used on the very next lines are
equally exposed to corruption by any other caller. 🔴

`ServoInformation` narrows this: `length`/`width`/`height` are properties
returning `self.servo.*` with setters that are literal `pass` statements. The
constructor builds `Servo(length, width, height, 0,0,0,0,0,0,0,0)` **only** when
`servo is None`; otherwise the three passed dimensions are silently unused, and
`super().__init__` is then called with `length=self.length` — i.e. the servo's
values, not the caller's. 🟡

### F6 — The aircraft aggregate and its projections 🟢

```
AirplaneConfiguration(name, total_mass_kg, wings, fuselages=None):
    self.total_mass       = total_mass_kg
    self._main_wing_index = 0
    self._main_wing       = self.wings[self._main_wing_index]   # 🟡 dead legacy path (Q-CT-3); IndexError when empty

to_dict():
    {"name", "total_mass_kg": self.total_mass,
     "wings": [w.__getstate__() for w in self.wings]}
    + "fuselages" only `if self.fuselages`

asb_airplane (cached_property):
    mm_to_m_scale = 1.0e-3
    wings     = [w.asb_wing(scale=mm_to_m_scale) for w in self.wings]
    fuselages = [f.asb_fuselage for f in self.fuselages] if self.fuselages else []
    asb.Airplane(name=..., xyz_ref=None, wings=..., fuselages=...,
                 propulsors=None,
                 analysis_specific_options={asb.AVL: {"profile_drag_coefficient": 0.}})
    self._asb_main_wing = asb_airplane.wings[self._main_wing_index]   # 🟡 side effect
```

Note `xyz_ref=None`: the reference point is left to AeroSandbox rather than being
taken from the design. 🟡 The app's own converter
(`aeroplane_schema_to_asb_airplane`) sets it explicitly, which is one more reason
the two ASB paths are not interchangeable.

### F7 — Installing the CadQuery extensions 🟢

```
import cad_designer.cq_plugins
  → from .fix_shape.fix_shape import fix_shape
  → import .segmentToEdge      # Sketch.segmentToEdge
  → import .display            # Workplane.display  (@conditional_execute)
  → import .fix_shape          # Workplane.fix_shape
  → import .offest3D           # Workplane.offset3D   (directory name misspelled)
  → import .sew_fix_shape      # Workplane.sewAndFix
  → import .wing               # Workplane.airfoil / .wing_root_segment / .wing_segment

# NOT imported: .scaleXyz  → recorded for removal (Q-CT-5 / P-DEAD-0) 🟢
```

```
conditional_execute(env_var_name)(func)(self, *args, **kwargs):
    env_var = os.getenv(env_var_name)
    if env_var is not None and env_var.upper() in ["1", "ON", "TRUE", "ENABLED"]:
        return func(self, *args, **kwargs)
    logging.warning(f"function '{func.__name__}' has been called, but has not been "
                    f"executed as '{env_var_name}' is not set.")
    return self
```

The `return self` is what keeps `.display()` usable mid-chain
(`shape.display(...).cut(other)`), and it is why the disabled path is a genuine
no-op rather than a `None` propagation bug. 🟢

## Alternative Flows

- **Non-orthonormal or mirrored basis** — `InvalidRotationMatrixException` during
  `CoordinateSystem.__init__`, before any geometry exists. 🟢
- **Serialised `euler_xyz` present** — ignored; recomputed from the direction
  vectors. 🟢
- **Missing keys in `from_json_dict`** — each direction falls back to the
  identity basis and the origin to `[0,0,0]`, so `from_json_dict({})` yields a
  valid identity frame rather than raising. 🟢
- **Spar with an explicit vector** — normalised; the origin is still derived if
  absent. 🟢
- **Spar in `follow` mode** — the origin chains off the previous segment's spar
  (`prev.origin + prev.vector * prev.length`) rather than the standard
  resolution. 🟢
- **Unknown `WingConfiguration.parameters`** — `ValueError` whose message names
  `'absolute'`, a value the code never accepts. 🟡
- **`ServoInformation` given both dimensions and a `servo`** — the dimensions are
  silently ignored. 🟡
- **Write to `ServoInformation.height`** — silently swallowed by the no-op
  setter. 🟢
- **`AirplaneConfiguration` with an empty `wings` list** — `IndexError` at
  construction. 🟡 Unmapped by any caller, so it surfaces as a 500.
- **`AirplaneConfiguration` with `fuselages=None`** — `to_dict` omits the key
  entirely and `asb_airplane` passes `[]`. 🟢
- **`DISPLAY_CONSTRUCTION_STEP` set to an unrecognised value** (`"yes"`, `"0"`) —
  treated as disabled; the warning fires. 🟢
- **CadQuery, SciPy, NumPy or AeroSandbox absent** — `ImportError` at import
  time; consumers guard (ADR 0017). Note `AirplaneConfiguration` imports
  `aerosandbox` at module scope, so importing that one file pulls in ASB even
  when only `to_dict()` is wanted. 🟡

## Dependencies

- **CadQuery / OCCT** — `Workplane`, `Plane`, and the `OCP.gp` primitives
  (`gp_Pnt`, `gp_Vec`, `gp_Dir`, `gp_Ax1`, `gp_XYZ`) used by the placement
  classes.
- **NumPy** — matrix construction, `allclose`, `linalg.det` in `CoordinateSystem`.
- **SciPy** — `scipy.spatial.transform.Rotation` for the Euler decomposition.
- **pydantic** — `confloat`, `PositiveFloat`, `NonNegativeFloat`,
  `BeforeValidator`, `Field` in `types.py` and the component constructors.
- **AeroSandbox** — imported at module scope by `AirplaneConfiguration` and the
  `cad_designer/aerosandbox/` bridge.
- **`cad_designer/aerosandbox/`** — `aerodynamic_calculations` (stall speed,
  static longitudinal stability, `CL_max`, best L/D, motor down/right-thrust
  estimation, incidence suggestion) and `classification` (Cm_α / Cl_β / Cn_β →
  `StabilityLevel` bands) are consumed by `airplane_analysis`.
- **Consumers:** every wing and fuselage Creator (`get_wing_workplane`,
  the `*Information` classes); `wing-design`'s spar solver and
  `app/converters/`; `cad-generation`'s worker (rebuilds a `WingConfiguration`);
  `aeroplane-core` (the `AirplaneConfiguration` export payload).

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Millimetres and a wing-local frame inside CAD, metres outside | ADR 0001; `cad_designer/CLAUDE.md` §Conventions | 🟢 |
| Geometry is a **chain of relative coordinate systems**, one per airfoil, rather than absolute placement | `CoordinateSystem` class docstring l.16-27 | 🟢 |
| A frame is validated at construction, so an invalid basis can never reach a loft | `CoordinateSystem.py:94-95` | 🟢 |
| The direction vectors are the source of truth; `euler_xyz` is derived and never trusted from input | `from_json_dict` l.112-117 | 🟢 |
| Tight, explicit tolerances (`atol=1e-6`) rather than exact equality | `CoordinateSystem.py:78-79` | 🟢 |
| A spar defaults to the quarter chord, centred on the camber line | `WingConfiguration.py:355-362` | 🟢 |
| A supplied spar vector is normalised, so magnitude cannot leak into geometry | `WingConfiguration.py:368` | 🟢 |
| Two wing parameterisations (`aerosandbox` / `relative`) selected by a field, not by subclassing | `get_wing_workplane` l.388-394 | 🟢 |
| Per-segment workplanes are cached because the transform chain is walked per rib | `get_wing_workplane` docstring | 🟢 |
| Servo dimensions are a **projection** of the catalogue part, not independently settable | `ServoInformation.py:30-35` | 🟢 |
| Components rotate about their **corner** point in X→Y→Z, not about their centre | `ComponentInformation.py:26-38` | 🟢 |
| Engine thrust angles are expressed as rotations rather than as a separate concept | `EngineInformation` `down_thrust → rot_y`, `side_thrust → rot_z` | 🟢 |
| The ASB projection is a `cached_property`, computed once per aircraft object | `AirplaneConfiguration.py:165` | 🟢 |
| CadQuery extensions install as an import side effect, so no consumer must remember them | `cq_plugins/__init__.py`; `GeneralJSONEncoderDecoder.py:7` | 🟢 |
| Visual debugging is an env-gated no-op returning `self`, preserving the fluent chain | `general_decorators.py:14-19` | 🟢 |
| The dead perpendicular-spare branch stays | ADR 0002; `cad_designer/CLAUDE.md`; `WingConfiguration.py:363-365` | 🟢 |

## Internal State

- **Per `CoordinateSystem`** — `xDir`, `yDir`, `zDir`, `origin` (lists) and the
  derived `euler_xyz`. Immutable in practice: nothing recomputes `euler_xyz`
  after construction, so mutating a direction vector afterwards would leave the
  two inconsistent. 🟡
- **Per `WingConfiguration`** — the cached per-segment workplanes (docstring),
  plus the `parameters` discriminator that selects the transform chain. Spar
  resolution **mutates the `Spare` objects in place**, writing
  `spare_position_factor`, `spare_vector` and `spare_origin` back onto them —
  which is exactly why `wing-design` needs
  `should_preserve_normal_spare` to protect solver output. 🟢
- **Per `ServoInformation`** — `_corner_vecs`, eight `gp_Vec` corners
  precomputed at construction from the resolved dimensions; stale if the backing
  `Servo` were ever mutated. 🟡
- **Per `AirplaneConfiguration`** — `_main_wing_index`, `_main_wing`, the
  `asb_airplane` cache and the `_asb_main_wing` written as its side effect.
- **Process-global, mutable** 🟢 **Carve-out granted, narrowly: fix the aliasing only** (`Q-CT-2`, maintainer-answered). The other two findings inside the frozen layer are documented, not fixed (ADR 0002). — `gp_DX`, `gp_DY`, `gp_DZ` in
  `ComponentInformation`; the monkey-patched `Workplane`/`Sketch` namespaces;
  the `DISPLAY_CONSTRUCTION_STEP` environment variable.

## Observability

- **`Workplane.display`** is the only instrumentation this slice adds, and it is
  disabled by default. When enabled it is the event source
  `construction-plans` streams over SSE; when disabled it emits one
  `logging.warning` per call naming the function and the variable
  (`general_decorators.py:18`). 🟡 High-volume by construction — every Creator
  calls it at least once per execution.
- **No logging in `CoordinateSystem`, `WingConfiguration`'s spar resolution, or
  the `*Information` classes.** Failures are exceptions; successes are silent.
  🟢
- **No metrics or traces.** Diagnostics for a build belong to
  `construction-plans` and `cad-generation`. 🟢
- 🔴 **The silent-wrongness failure mode has no instrumentation at all.** Not addressed by the validation interview. A
  corrupted `gp_DZ`, an ignored `ServoInformation` dimension or a
  mis-parameterised workplane produces a wrong solid with no log line, no
  warning and no assertion — which is precisely the risk ADR 0002 cites for
  freezing the layer.

## Risks and Gaps

- 🔴 **`get_z_axis` corrupts `gp_DX`/`gp_DY`/`gp_DZ` process-wide.** `z = gp_DZ`
  is an alias and `gp_Dir.Rotate` mutates in place. After the first call with a
  non-zero rotation, every consumer of those singletons — including the very
  next `get_middle_point` — uses rotated axes. This is a *silent* geometry
  corruption, the exact failure mode ADR 0002 warns about.
- 🔴 **`get_middle_point`'s z term uses `self.length/2`** where `height/2` reads
  as intended, and the sign pattern (`+x`, `−y`, `−z`) is undocumented. Whether
  it is a bug or a deliberate corner convention cannot be determined from the
  code.
- 🟢 **`euler_xyz` is display/serialisation only** — no consumer depends on the intrinsic/extrinsic distinction (`Q-CT-4`, resolved by code lookup). Previously the rotation units were unspecified: `rot_x/rot_y/rot_z` are bare floats fed
  to `gp_Ax1` rotations, which OCCT defines in **radians**, while
  `EngineInformation`'s `down_thrust`/`side_thrust` read naturally as degrees.
  Nothing in the classes, callers or docstrings resolves it.
- 🔴 **`AirplaneConfiguration` raises `IndexError` on an empty `wings` list**, an
  unmapped exception that surfaces as a 500 rather than a validation error.
- 🔴 **`_main_wing_index = 0`** is a dormant duplicate of the gh-788
  reference-area bug on an ASB path the app does not currently call.
- 🔴 **`get_wing_workplane`'s error message names `'absolute'`**, a value the
  code never accepts — suggesting a rename to `"aerosandbox"` left the message
  behind.
- 🔴 **`scaleXyz` is never installed** (`cq_plugins/__init__.py` does not import
  it) and its implementation has a typo'd parameter `y_sacle`. The package also
  ships a stale `offest3D/.ipynb_checkpoints/` copy, and the plugin directory
  itself is misspelled `offest3D`.
- 🔴 **`InvalidRotationOrderException` is declared and never raised** — a
  placeholder for order validation that was never written, while the order
  parameter is silently lower-cased instead.
- 🟡 **`euler_xyz` is extrinsic despite the caller requesting `'XYZ'`.** Any
  consumer that treats it as intrinsic reads a different rotation for
  non-commuting combinations. Whether any consumer does is unverified.
- 🟡 **`ServoInformation` silently ignores constructor dimensions** when a
  `servo` is supplied, and its `_corner_vecs` are frozen at construction.
- 🟡 **`CoordinateSystem` never revalidates.** Mutating a direction vector after
  construction leaves `euler_xyz` stale and the basis unchecked.
- 🟡 **Spar resolution mutates `Spare` objects in place**, which is why the
  gh-1053 preservation guard exists one layer up in `wing-design`.
- 🟡 **`AirplaneConfiguration` imports AeroSandbox at module scope**, so
  importing the aggregate for a pure `to_dict()` export pulls in the whole ASB
  stack.
- 🟡 **`asb_airplane` passes `xyz_ref=None`**, unlike the app's own converter —
  one more reason the two ASB paths are not interchangeable.
