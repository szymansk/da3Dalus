# wingconfiguration-coordinate-system

> Use-case specification, nested under the module
> [`cad-designer-topology`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: cad-designer-topology
> (`CoordinateSystem`, `WingConfiguration`, the `*Information` classes,
> `AirplaneConfiguration`, `cq_plugins`),
> `_reversa_sdd/data-dictionary.md` §Component classes, §Domain literal types.
>
> ⚠ **This slice is entirely inside the FROZEN layer (ADR 0002)** —
> `aircraft_topology/**` is read-only, and several of the rules below describe
> defects that are *deliberately* left in place.

## Overview

`wingconfiguration-coordinate-system` is the **geometric vocabulary** of the CAD
library: the millimetre wing-local frame, the chained coordinate systems that
place each rib, the spar origin/vector resolution that turns a designer's intent
into a 3D line, the component-placement classes for servos and engines, and the
CadQuery extensions the Creators build on. It is the layer where a wrong sign or
a wrong unit produces a *plausible but incorrect solid* rather than an error. 🟢

## Responsibilities

- Define the **millimetre, wing-local frame** (origin at the root leading edge,
  z up) that every dimension in `cad_designer/` is expressed in. 🟢
- Provide `CoordinateSystem`: a validated orthonormal basis plus origin, with a
  derived Euler decomposition, forming the chain of relative transforms that
  positions each `Airfoil` and `WingSegment`. 🟢
- Resolve a `Spare`'s **origin and direction vector** from its
  `spare_position_factor`, defaulting to quarter chord. 🟢
- Build a per-segment CadQuery `Workplane` from the segment's transform chain,
  in either the `"aerosandbox"` or the `"relative"` parameterisation. 🟢
- Provide the **domain literal types** (`Factor`, `DihedralInDegrees`,
  `WingSides`, `WingSegmentType`, `TipType`, `CoordinateSystemBase`, `ShapeId`,
  `CreatorId`) shared with `app/schemas/`. 🟢
- Provide the **component placement classes** — `ComponentInformation`,
  `ServoInformation`, `EngineInformation`, `Position`, `Printer3dSettings` —
  that locate hardware inside the airframe. 🟢
- Provide `AirplaneConfiguration`: the whole-aircraft aggregate, its export
  envelopes and its AeroSandbox projection. 🟢
- Install the **CadQuery extensions** (`cq_plugins`) and the
  `@conditional_execute` / `@fluent_init` decorators. 🟢

**Explicitly NOT this use case's responsibility:** the Creator contract and tree
traversal (→ [`../creator-execution-model/`](../creator-execution-model/requirements.md)),
the `$TYPE` plan serialisation (→
[`../json-polymorphic-roundtrip/`](../json-polymorphic-roundtrip/requirements.md)
— note that the topology classes' own `__getstate__`/`from_json_dict` format is
documented there as the *second* system), the spar **sizing and layout solver**
and section geometry (→ [`wing-design`](../../wing-design/requirements.md), which
owns every formula even though `geometry/` lives in this package), the
millimetre↔metre conversion functions themselves (`app/converters/`), the
fuselage slicer (→ `fuselage-design`), and the wing topology constructors
`WingConfiguration` / `WingSegment` / `Airfoil` / `Spare` / `TrailingEdgeDevice`
/ `Turbulator` field-by-field, which are tabled in
[`wing-design`](../../wing-design/design.md).

## Business Rules

> IDs are inherited verbatim from [`../requirements.md`](../requirements.md).

- **BR-CT2 — Millimetres throughout, wing-local frame.** 🟢 Every length in
  `cad_designer/` is millimetres; the frame origin is the root leading edge with
  z up (`cad_designer/CLAUDE.md` §Conventions). `app/converters/` scales to
  metres for the database and AeroSandbox (`scale = 0.001` mm→m,
  `1000.0` m→mm). There is **no type-level unit** — the invariant is positional
  and enforced only at the converter boundary. ADR 0001.
- **BR-CT21 — Literal types normalise case, and the direction differs.** 🟢
  (`cad_designer/airplane/types.py:5-38`)

  ```
  Factor               = confloat(ge=0, le=1.0)
  DihedralInDegrees    = confloat(ge=-180.0, le=180.0)
  CoordinateSystemBase = Literal["world","wing","root_airfoil","tip_airfoil"]   .lower()
  WingSegmentType      = Literal["root","segment","tip"]                        .lower()
  TipType              = Literal["flat","round"]                                .lower()
  WingSides            = Literal["LEFT","RIGHT","BOTH"]                         .upper()
  ShapeId / CreatorId  = NewType(..., str)          # documentation, no validation
  ```

  Each `BeforeValidator` is `lambda x: x.lower() if isinstance(x, str) else x`
  (or `.upper()`), so a non-string passes through untouched and then fails the
  `Literal` check.
- **BR-CT22 — `CoordinateSystem` validates before it decomposes, and the result
  is extrinsic.** 🟢 (`aircraft_topology/wing/CoordinateSystem.py:29-99`)
  Construction stores `xDir`, `yDir`, `zDir`, `origin` as **lists**, builds
  `R = np.matrix([xDir, yDir, zDir]).T`, and requires

  ```
  R.shape == (3, 3)
  np.allclose(R @ R.T, I, atol=1e-6)          # orthonormal
  np.isclose(det(R), 1.0, atol=1e-6)          # right-handed, not mirrored
  ```

  or raises `InvalidRotationMatrixException`. It then computes
  `euler_xyz = Rotation.from_matrix(R).as_euler(order.lower(), degrees=True)`.
  🟡 The call site passes `'XYZ'` and the implementation lower-cases it (l.98) —
  in SciPy upper-case means **intrinsic** and lower-case **extrinsic**, so the
  stored decomposition is always extrinsic regardless of the requested order.
  `InvalidRotationOrderException` (l.7) is declared and **never raised**. 🟡 Recorded for removal under `P-DEAD-0`; stated, not executed (ADR 0002).
  `from_json_dict` defaults each direction to the identity basis and the origin
  to `[0,0,0]`, and **recomputes** `euler_xyz` rather than reading the
  serialised value — a hand-edited `euler_xyz` is silently discarded. 🟢
- **BR-CT27 — Spar origin/vector resolution, and the branch that cannot be
  reached.** 🟢 `WingConfiguration._set_standard_spare_origin_vector`
  (l.354-372):

  ```python
  if spare.spare_position_factor is None:
      spare.spare_position_factor = 0.25                  # l.355-356
  if spare.spare_vector is None and spare.spare_position_factor is not None:
      spare.spare_vector, _, _, _ = self._get_standard_spare_origin_and_vector(...)
  elif spare.spare_vector is None:                        # l.363 → UNREACHABLE
      spare.spare_vector = self.get_wing_workplane(segment_number).plane.yDir
  else:
      spare.spare_vector = spare.spare_vector.normalized()
  if spare.spare_origin is None:
      _, spare.spare_origin, _, _ = self._get_standard_spare_origin_and_vector(...)
  ```

  The `0.25` default makes the second half of the first condition always true,
  which makes the `elif` — the "perpendicular spare" fallback — dead.
  `cad_designer/CLAUDE.md` names this branch explicitly and says it **stays**.
  Observable behaviour to preserve: a spar with neither factor nor vector lands
  on the quarter-chord standard vector; a supplied vector is **normalised**, not
  replaced; the origin is derived independently of the vector branch.
- **BR-CT32 — `get_wing_workplane`'s error message names a value it never
  accepts.** 🟡 (`WingConfiguration.py:389-394`)

  ```python
  if   self.parameters == "aerosandbox": all_trans = self._get_absolute_segment_coordinate_system(...)
  elif self.parameters == "relative":    all_trans = self._get_relative_segment_coordinate_system(...)
  else: raise ValueError(f"Unknown parameter type {self.parameters}, "
                         f"should be 'absolute' or 'relative'")
  ```

  The workplane is built from the transform's third column (normal), fourth
  column (origin) and first column (xDir), and is **cached for performance**
  (docstring). `ignore_nose_point` optionally omits the nose offset.
- **BR-CT23 — `ServoInformation` dimensions are read-only projections of its
  `Servo`.** 🟢 `length` / `width` / `height` are properties backed by
  `self.servo`, and their setters are **no-ops that silently swallow writes**
  (`ServoInformation.py:30-35`, with the literal comment
  *"Read-only property backed by self.servo"*). 🟡 The constructor's
  `height/width/length` arguments are used **only** to build a default
  `Servo(length, width, height, 0,0,0,0,0,0,0,0)` when `servo is None`; if a
  `servo` **is** supplied, those three arguments are silently ignored. The class
  also precomputes eight `_corner_vecs` from the resolved dimensions and adds
  `lever_length`.
- **BR-CT24 — `AirplaneConfiguration` requires at least one wing and hard-codes
  the main wing.** 🟢 (`airplane/AirplaneConfiguration.py:21-32`) `__init__`
  stores `name`, `total_mass` (from `total_mass_kg`), `wings`, `fuselages`, then
  immediately evaluates `self._main_wing = self.wings[self._main_wing_index]`
  with `_main_wing_index = 0` — so an **empty `wings` list raises `IndexError`
  at construction**. `asb_airplane` is a `cached_property` converting at
  `mm_to_m_scale = 1.0e-3`, passing `xyz_ref=None` and
  `analysis_specific_options = {asb.AVL: {"profile_drag_coefficient": 0.0}}`;
  🟡 it also assigns `self._asb_main_wing` as a side effect of the property.
- **BR-CT25 — `Workplane.display` is environment-gated.** 🟢
  `@conditional_execute("DISPLAY_CONSTRUCTION_STEP")`
  (`decorators/general_decorators.py:5-21`) runs the decorated function only when
  the variable is set **and** `env_var.upper() in ["1","ON","TRUE","ENABLED"]`;
  otherwise it logs
  `"function '<name>' has been called, but has not been executed as '<VAR>' is not set."`
  and **returns `self`**, so the fluent chain survives. This is the hook
  `construction-plans` toggles to stream shape events.
- **BR-CT26 — CadQuery extensions are installed by import, not by call.** 🟢
  `cq_plugins/__init__.py` imports `fix_shape`, `segmentToEdge`, `display`,
  `offest3D` (*sic* — the package directory name is misspelled),
  `sew_fix_shape` and `wing`, each of which monkey-patches its function onto
  `cq.Workplane` (or `cq.Sketch`) at import time. `@fluent_init`
  (`general_decorators.py:28-39`) adds a static `.init()` factory carrying the
  constructor signature minus `self`, and is applied to `WingConfiguration`
  only.
- **BR-CT29 — `ComponentInformation.get_z_axis` corrupts module-level
  singletons.** 🟢 **Carve-out granted, narrowly: fix the aliasing only** (`Q-CT-2`, maintainer-answered). The other two findings inside the frozen layer are documented, not fixed (ADR 0002). (`components/ComponentInformation.py:4-6, 33-38`)

  ```python
  gp_DX = gp_Dir(gp_XYZ(1, 0, 0))     # module-level singletons
  gp_DY = gp_Dir(gp_XYZ(0, 1, 0))
  gp_DZ = gp_Dir(gp_XYZ(0, 0, 1))

  def get_z_axis(self) -> gp_Dir:
      z = gp_DZ                        # ALIAS, not a copy
      z.Rotate(gp_Ax1(self.get_corner_point(), gp_DX), self.rot_x)
      ...
  ```

  `gp_Dir.Rotate` mutates **in place**, so `gp_DZ` is permanently rotated after
  the first call — and `gp_DX`/`gp_DY`, used as the rotation axes, are corrupted
  by any other caller in the same way. Every later consumer, including
  `get_middle_point` on any instance, sees rotated axes.
  Additionally (l.26-31): `get_middle_point` builds
  `gp_Vec(trans_x + length/2, trans_y − width/2, trans_z − length/2)` — the **z**
  term uses `length/2` where `height/2` reads as intended — and rotates about the
  corner point in **X → Y → Z** order. 🟢 **`euler_xyz` is display/serialisation only** — no consumer depends on the intrinsic/extrinsic distinction (`Q-CT-4`, resolved by code lookup). Rotation units are never stated while
  `gp_Ax1` rotation takes **radians** and `rot_*` are unlabelled floats.
- **BR-CT30 — `AirplaneConfiguration` carries a dormant copy of the gh-788
  reference-area bug.** 🟡 **Dead legacy path** — the second ASB entry point supersedes it (`Q-CT-3`, derived); it is the same "first wing is the main wing" error class that gh-788 fixed elsewhere. `_main_wing_index = 0` is the same "first wing is the
  main wing" assumption that made every coefficient ≈8× wrong for a tail-first
  import. gh-788 fixed the app converter to pick the largest-planform wing
  (`app/converters/model_schema_converters.py:761-817`); this copy was not
  touched. It is currently a **dead second ASB path** — the app builds an
  `AirplaneConfiguration` purely as an export payload
  (`aeroplane_service.py:288`) and uses `aeroplane_schema_to_asb_airplane` for
  all aerodynamics — so any future caller would silently inherit the bug.
- **BR-CT31 — 🟢 **The hinge-type literal keeps all five values; `round_inside`/`round_outside` are declared-but-unimplemented, and the implementation follows** (`Q-CT-5`, maintainer-answered). Measured: no stored row uses either, so there is no harm to a beta user. The genuinely dead items (`AbstractConstructionStep.construct`, `create_XYZ_ted_sketch`, the unimported `scaleXyz` plugin) are recorded for removal under `P-DEAD-0`, but **stated in the spec rather than executed**, because they sit inside the ADR 0002 freeze.** `cq_plugins/scaleXyz/__init__.py`
  registers `cq.Workplane.scaleXyz`, but `cq_plugins/__init__.py` never imports
  it and nothing else does, so the plugin is **never installed**; its
  implementation also has a typo'd parameter `y_sacle`
  (`scaleXyz/scaleXyz.py:6`). The package additionally ships a stale
  `offest3D/.ipynb_checkpoints/` copy.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-WC-01 | Express every length in millimetres in a wing-local frame with z up | Must | A 250 mm chord is the literal value `250.0`; the converter layer produces `0.25` m |
| RF-WC-02 | Provide the domain literal types with their documented bounds | Must | `Factor = 1.5` is rejected; `DihedralInDegrees = -200` is rejected |
| RF-WC-03 | Lower-case `CoordinateSystemBase`, `WingSegmentType`, `TipType`; upper-case `WingSides` | Should | `"Root"` validates to `"root"`; `"both"` validates to `"BOTH"` |
| RF-WC-04 | Pass non-string values through the case validators untouched | Should | An `int` input reaches the `Literal` check and is rejected there, not in the validator |
| RF-WC-05 | Construct a `CoordinateSystem` from three direction vectors and an origin, storing them as lists | Must | A tuple input is stored as a list and serialises as a JSON array |
| RF-WC-06 | Reject a non-orthonormal or mirrored basis | Must | `det R = −1` and a non-orthogonal basis both raise `InvalidRotationMatrixException` |
| RF-WC-07 | Derive `euler_xyz` in degrees at construction | Must | The identity basis yields `[0, 0, 0]` |
| RF-WC-08 | Recompute `euler_xyz` on load rather than trusting the serialised value | Should | A hand-edited `euler_xyz` in the JSON is provably ignored |
| RF-WC-09 | Default a missing direction vector to the identity basis and a missing origin to `[0,0,0]` on load | Should | `from_json_dict({})` yields the identity frame |
| RF-WC-10 | Default a spar's `spare_position_factor` to `0.25` when absent | Must | A spar with no factor and no vector lands on the quarter-chord standard vector |
| RF-WC-11 | Normalise a supplied `spare_vector` rather than replacing it | Must | A vector of length 3.0 becomes a unit vector in the same direction |
| RF-WC-12 | Derive a missing `spare_origin` independently of the vector branch | Must | A spar with an explicit vector but no origin still receives the standard origin |
| RF-WC-13 | Build a per-segment `Workplane` in `"aerosandbox"` or `"relative"` parameterisation | Must | Both modes produce a plane; an unknown mode raises `ValueError` |
| RF-WC-14 | Cache the per-segment workplane | Should | Repeated calls for the same segment do not recompute the transform chain |
| RF-WC-15 | Support `ignore_nose_point` when computing a segment workplane | Could | The origin differs by exactly the nose offset between the two calls |
| RF-WC-16 | Provide `ComponentInformation` placement with X→Y→Z rotation about the corner point | Must | Rotating only `rot_z` leaves the x and y corner coordinates on the expected circle |
| RF-WC-17 | Back `ServoInformation` dimensions with its `Servo`, with no-op setters | Must | `servo_info.height = 99` is provably a no-op |
| RF-WC-18 | Build a default `Servo` from the constructor dimensions only when none is supplied | Must | Supplying both a `servo` and explicit dimensions provably uses the servo's |
| RF-WC-19 | Map `EngineInformation.down_thrust → rot_y` and `side_thrust → rot_z` | Should | A 3° down-thrust produces `rot_y == 3` |
| RF-WC-20 | Provide `Printer3dSettings` defaults of 0.24 / 0.42 / 0.075 mm | Should | An aircraft with no `printer_settings` component builds with these values |
| RF-WC-21 | Require at least one wing on `AirplaneConfiguration` | Must | An empty `wings` list raises at construction, not later |
| RF-WC-22 | Export an aircraft to a dict, a JSON file and a zip of per-object JSONs | Should | The zip contains one file per wing and per fuselage; `"fuselages"` is omitted from the dict when falsy |
| RF-WC-23 | Convert an aircraft to an AeroSandbox airplane at `mm_to_m_scale = 1e-3` | Could | A 1000 mm chord becomes 1.0 m; `profile_drag_coefficient = 0.0` is set for AVL |
| RF-WC-24 | Install the CadQuery extensions on import of the plugin package | Must | After the import, `Workplane.sewAndFix` and `Sketch.segmentToEdge` exist |
| RF-WC-25 | Gate `Workplane.display` on `DISPLAY_CONSTRUCTION_STEP` and return `self` when disabled | Must | With the variable unset, `display()` logs a warning and the chain continues unchanged |
| RF-WC-26 | Provide a static `.init()` factory on `WingConfiguration` | Could | `WingConfiguration.init(...)` constructs an instance; its signature omits `self` |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Correctness | A rotation basis is validated **before** decomposition, so a malformed frame fails loudly instead of producing plausible angles | `CoordinateSystem.py:76-95` | 🟢 |
| Correctness | Tolerances are explicit and tight (`atol=1e-6` for both orthonormality and determinant) | `CoordinateSystem.py:78-79` | 🟢 |
| Correctness | A supplied spar vector is normalised, so magnitude can never leak into the geometry | `WingConfiguration.py:368` | 🟢 |
| Correctness | `euler_xyz` is derived, never trusted from input — the direction vectors are the single source of truth | `CoordinateSystem.py:112-117` | 🟢 |
| Performance | Per-segment workplanes are cached, because the transform chain is walked for every rib | `get_wing_workplane` docstring | 🟢 |
| Performance | `asb_airplane` is a `cached_property`, so the ASB conversion happens once per aircraft object | `AirplaneConfiguration.py:165` | 🟢 |
| Portability | The whole slice requires CadQuery/OCCT, SciPy and NumPy; AeroSandbox is a hard import of `AirplaneConfiguration` | module imports; ADR 0017 | 🟢 |
| Observability | Visual debugging is opt-in via an env var with zero cost when disabled, and preserves the fluent chain | `general_decorators.py:5-21` | 🟢 |
| Safety | 🔴 Rotation units are unspecified on the placement classes, while OCCT expects radians | `ComponentInformation.py:28-31` | 🔴 |
| Concurrency | 🔴 `gp_DX/gp_DY/gp_DZ` are mutable module-level singletons shared across every instance and every thread | `ComponentInformation.py:4-6, 33-38` | 🔴 |

## Acceptance Criteria

```gherkin
Feature: Coordinate system construction

  Scenario: A valid orthonormal basis is accepted and decomposed
    Given the identity direction vectors and the origin [0,0,0]
    When a CoordinateSystem is constructed
    Then euler_xyz is [0, 0, 0]
    And xDir, yDir, zDir and origin are stored as lists

  Scenario: A non-orthonormal basis is rejected
    Given direction vectors that are not mutually perpendicular
    When a CoordinateSystem is constructed
    Then InvalidRotationMatrixException is raised
    And no Euler angles are produced

  Scenario: A mirrored basis is rejected
    Given direction vectors whose determinant is -1
    When a CoordinateSystem is constructed
    Then InvalidRotationMatrixException is raised

  Scenario: A serialised euler_xyz is ignored on load
    Given a JSON dict whose euler_xyz is [99, 99, 99]
    And whose direction vectors are the identity basis
    When from_json_dict is called
    Then the resulting euler_xyz is [0, 0, 0]

  Scenario: Missing fields fall back to the identity frame
    Given an empty JSON dict
    When from_json_dict is called
    Then xDir is [1,0,0], yDir is [0,1,0], zDir is [0,0,1] and origin is [0,0,0]

Feature: Spar origin and vector resolution

  Scenario: A bare spar lands on the quarter chord
    Given a spar with no spare_position_factor, no spare_vector and no spare_origin
    When the standard origin and vector are resolved for its segment
    Then spare_position_factor is 0.25
    And spare_vector is the standard vector for that factor
    And spare_origin is the standard origin for that factor

  Scenario: A supplied vector is normalised, not replaced
    Given a spar whose spare_vector has length 3.0
    When the standard origin and vector are resolved
    Then spare_vector points in the same direction
    And its length is 1.0

  Scenario: An explicit vector still gets a derived origin
    Given a spar with an explicit spare_vector and no spare_origin
    When the standard origin and vector are resolved
    Then spare_origin is the standard origin for its position factor

Feature: Segment workplane

  Scenario: Both parameterisations produce a plane
    Given a wing configuration with parameters "aerosandbox"
    When the workplane for segment 0 is requested
    Then a Workplane is returned whose origin is the segment origin
    And the same holds for parameters "relative"

  Scenario: An unknown parameterisation is rejected
    Given a wing configuration whose parameters is "absolute"
    When the workplane for segment 0 is requested
    Then a ValueError is raised
    # NOTE: the message names 'absolute' as if it were valid — see BR-CT32

Feature: Component placement

  Scenario: A servo's dimensions come from its Servo
    Given a ServoInformation built with an explicit Servo
    When length, width and height are read
    Then they equal the Servo's values
    And assigning to them changes nothing

  Scenario: Constructor dimensions build a default Servo only when none is given
    Given a ServoInformation built with dimensions and no Servo
    Then a default Servo carrying those dimensions is created
    And when a Servo is supplied instead, the passed dimensions are ignored

  Scenario: Engine thrust angles map onto rotations
    Given an EngineInformation with down_thrust 3 and side_thrust 2
    Then rot_y is 3
    And rot_z is 2

Feature: Aircraft aggregate

  Scenario: An aircraft with no wings cannot be constructed
    Given an empty list of wings
    When an AirplaneConfiguration is constructed
    Then an IndexError is raised while resolving the main wing

  Scenario: An aircraft without fuselages omits the key
    Given an aircraft with two wings and no fuselages
    When to_dict is called
    Then the result has no "fuselages" key
    And "wings" contains two serialised wings

  Scenario: The ASB projection converts millimetres to metres
    Given a wing whose root chord is 1000 mm
    When asb_airplane is read
    Then the corresponding ASB chord is 1.0

Feature: CadQuery extensions

  Scenario: Importing the plugin package installs the methods
    When cad_designer.cq_plugins is imported
    Then Workplane.fix_shape, offset3D, display, sewAndFix, airfoil,
      wing_root_segment and wing_segment exist
    And Sketch.segmentToEdge exists

  Scenario: The display hook is inert when the variable is unset
    Given DISPLAY_CONSTRUCTION_STEP is not set
    When a creator calls workplane.display(name="x")
    Then a warning naming the function and the variable is logged
    And the same workplane is returned

  Scenario: The display hook fires for each accepted value
    Given DISPLAY_CONSTRUCTION_STEP is one of "1", "on", "True" or "ENABLED"
    When a creator calls workplane.display(name="x")
    Then the decorated function executes

  Scenario: An unrecognised value leaves the hook disabled
    Given DISPLAY_CONSTRUCTION_STEP is "yes"
    When a creator calls workplane.display(name="x")
    Then the decorated function does not execute
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| The millimetre wing-local frame (RF-WC-01) | Must | Every dimension in the package and every converter depends on it; a 1000× error is the most common defect class in this codebase |
| `CoordinateSystem` construction + validation (RF-WC-05…RF-WC-07) | Must | The chain of relative transforms that positions every rib; an invalid frame silently deforms the whole wing |
| Spar origin/vector resolution (RF-WC-10…RF-WC-12) | Must | Consumed directly by `wing-design`'s solver and by the CAD insertion path |
| Segment workplane (RF-WC-13) | Must | Every wing Creator builds on it |
| Domain literal types (RF-WC-02) | Must | Shared vocabulary with `app/schemas/`; the bounds are the only validation the topology layer has |
| `AirplaneConfiguration` wing precondition (RF-WC-21) | Must | Silent `IndexError` at construction is the current contract and callers rely on the aggregate being non-empty |
| `ServoInformation` backing + no-op setters (RF-WC-17, RF-WC-18) | Must | Servo cut-outs are built from these dimensions; a silently ignored write produces a wrong pocket |
| Plugin installation on import (RF-WC-24) | Must | Creators call `sewAndFix` and `airfoil` directly; without the import they are `AttributeError`s |
| Display gate (RF-WC-25) | Must | `construction-plans`' SSE streaming depends on the exact accepted-value set |
| Case normalisation (RF-WC-03, RF-WC-04) | Should | Tolerance for hand-authored JSON and frontend payloads; canonical values always validate |
| `euler_xyz` recomputation on load (RF-WC-08, RF-WC-09) | Should | Defensive; the direction vectors are the source of truth either way |
| Workplane caching (RF-WC-14) | Should | Performance only — the transform chain is walked per rib |
| `EngineInformation` thrust mapping (RF-WC-19) | Should | Used by the engine-mount Creators; a small, well-defined mapping |
| `Printer3dSettings` defaults (RF-WC-20) | Should | `construction-plans` falls back to exactly these when no component row exists |
| Export envelopes (RF-WC-22) | Should | Used by `aeroplane-core`'s export payload |
| `ignore_nose_point` (RF-WC-15) | Could | A specialised option on the workplane query |
| `asb_airplane` (RF-WC-23) | Could | A second ASB path the app does not use |
| `fluent_init` (RF-WC-26) | Could | Ergonomic sugar applied to exactly one class |
| Fixing the perpendicular-spare dead branch | Won't | Deliberately frozen (BR-CT27); named explicitly in `cad_designer/CLAUDE.md` |
| Fixing `gp_D*` mutation in place | Won't (this module) | Frozen file; a re-implementation must not reproduce it (see `tasks.md` T-WC-16) |
| Fixing `_main_wing_index = 0` in place | Won't (this module) | Dormant path; the live fix is in `app/converters/` (gh-788) |
| `scaleXyz` plugin | Won't | Never imported, never installed, and typo'd |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `cad_designer/airplane/types.py` (38 l.) | `Factor`, `DihedralInDegrees`, `CoordinateSystemBase`, `WingSegmentType`, `TipType`, `WingSides`, `ShapeId`, `CreatorId` | 🟢 |
| `cad_designer/airplane/aircraft_topology/wing/CoordinateSystem.py` (145 l.) | `CoordinateSystem`, `_is_valid_rotation_matrix`, `_rotation_matrix_to_euler_angles`, `__getstate__`, `from_json_dict`, `from_json`, `save_to_json`, `InvalidRotationOrderException` (dead) | 🟢 read-only |
| `cad_designer/airplane/aircraft_topology/wing/WingConfiguration.py` (1 050 l.) | `_set_standard_spare_origin_vector`, `_get_standard_spare_origin_and_vector`, `get_wing_workplane`, `_get_absolute_segment_coordinate_system`, `_get_relative_segment_coordinate_system` | 🟢 read-only |
| `cad_designer/airplane/aircraft_topology/components/ComponentInformation.py` (38 l.) | `gp_DX/DY/DZ`, `ComponentInformation`, `get_corner_point`, `get_middle_point`, `get_z_axis` | 🟢 read-only |
| `cad_designer/airplane/aircraft_topology/components/ServoInformation.py` | `ServoInformation`, the read-only dimension properties, `_corner_vecs` | 🟢 read-only |
| `cad_designer/airplane/aircraft_topology/components/EngineInformation.py` | `EngineInformation`, `down_thrust → rot_y`, `side_thrust → rot_z` | 🟢 read-only |
| `cad_designer/airplane/aircraft_topology/Position.py` | `Position`, `get_x/y/z` | 🟢 read-only |
| `cad_designer/airplane/aircraft_topology/printer3d/Printer3dSettings.py` | `Printer3dSettings` defaults | 🟢 read-only |
| `cad_designer/airplane/aircraft_topology/airplane/AirplaneConfiguration.py` | `__init__`, `to_dict`, `save_to_json`, `save_to_zip`, `asb_airplane`, `airplane_analysis` | 🟢 read-only |
| `cad_designer/cq_plugins/__init__.py` + submodules | `fix_shape`, `offest3D`, `display`, `sew_fix_shape`, `wing`, `segmentToEdge`; unregistered `scaleXyz` | 🟢 |
| `cad_designer/decorators/general_decorators.py` (39 l.) | `conditional_execute`, `fluent_init` | 🟢 |
| `cad_designer/aerosandbox/aerodynamic_calculations.py`, `classification.py`, `wing_roundtrip.py` (857 l.) | stall speed, `CL_max`, best L/D, static longitudinal stability, `StabilityLevel` bands, the three-level round-trip harness | 🟢 |
