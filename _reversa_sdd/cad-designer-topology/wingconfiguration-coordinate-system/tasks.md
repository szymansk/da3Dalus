# wingconfiguration-coordinate-system — Implementation Tasks

> Use-case task list, nested under the module
> [`cad-designer-topology`](../tasks.md).
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
>
> ⚠ **This slice is entirely inside the FROZEN layer (ADR 0002).** These tasks
> describe **what a re-implementation must reproduce**, not edits to make in
> `cad_designer/aircraft_topology/`. The `### Preservation constraints` section
> is unusually large here because this is where the deliberately-unfixed defects
> live.

## Prerequisites

- [ ] CadQuery / OCCT available — `Workplane`, `Plane` and the `OCP.gp`
      primitives (`gp_Pnt`, `gp_Vec`, `gp_Dir`, `gp_Ax1`, `gp_XYZ`) are used
      directly (ADR 0017).
- [ ] NumPy and SciPy — matrix validation and
      `scipy.spatial.transform.Rotation` for the Euler decomposition.
- [ ] pydantic v2 — `confloat`, `PositiveFloat`, `NonNegativeFloat`,
      `BeforeValidator`, `Field`.
- [ ] AeroSandbox — imported at module scope by `AirplaneConfiguration`.
- [ ] **The unit decision is settled**: millimetres inside, metres outside
      (ADR 0001). Every task below assumes it.
- [ ] **A decision on rotation units** for the placement classes
      (→ T-WC-18). This blocks any faithful reproduction of component placement.
- [ ] The wing topology classes (`WingConfiguration`, `WingSegment`, `Airfoil`,
      `Spare`, `TrailingEdgeDevice`, `Turbulator`) exist — their field-by-field
      contracts belong to
      [`wing-design`](../../wing-design/tasks.md), not to this slice.

## Tasks

### Domain vocabulary

- [ ] **T-WC-01 — Domain literal types.**
  `Factor = confloat(ge=0, le=1.0)`;
  `DihedralInDegrees = confloat(ge=-180.0, le=180.0)`;
  `CoordinateSystemBase`, `WingSegmentType`, `TipType` as `Literal`s wrapped in
  `Annotated[..., Field(description=...), BeforeValidator(lower)]`;
  `WingSides` the same but **upper**-cased; `ShapeId` / `CreatorId` as
  `NewType(..., str)` carrying documentation only.
  Each validator must be guarded with `isinstance(x, str)`.
  - Legacy origin: `cad_designer/airplane/types.py:5-38`
  - Definition of done: `"Root"` validates to `"root"`; `"both"` validates to
    `"BOTH"`; a non-string reaches the `Literal` check and is rejected there;
    `Factor = 1.5` and `DihedralInDegrees = -200` are rejected.
  - Confidence: 🟢

### Coordinate systems

- [ ] **T-WC-02 — `CoordinateSystem` construction.**
  Accept `xDir`, `yDir`, `zDir`, `origin` as tuple **or** list; store all four as
  **lists**; build `R = matrix([xDir, yDir, zDir]).T`; derive `euler_xyz` in
  degrees at construction.
  - Legacy origin: `aircraft_topology/wing/CoordinateSystem.py:29-53`
  - Definition of done: a tuple input is stored as a list and serialises as a
    JSON array; the identity basis yields `euler_xyz == [0, 0, 0]`.
  - Confidence: 🟢

- [ ] **T-WC-03 — Rotation-matrix validation.**
  `_is_valid_rotation_matrix(R)`: shape `(3,3)`,
  `np.allclose(R @ R.T, I, atol=1e-6)` **and**
  `np.isclose(det(R), 1.0, atol=1e-6)`. Raise
  `InvalidRotationMatrixException("The provided matrix is not a valid rotation
  matrix.")` from `_rotation_matrix_to_euler_angles` when it fails.
  - Legacy origin: `CoordinateSystem.py:65-99`
  - Definition of done: a non-orthogonal basis raises; a **mirrored** basis
    (`det = −1`) raises; a basis off by `5e-7` is accepted and one off by `5e-5`
    is rejected, pinning the tolerance.
  - Confidence: 🟢

- [ ] **T-WC-04 — Euler decomposition.**
  `Rotation.from_matrix(R).as_euler(order.lower(), degrees=True)`.
  **Document the convention explicitly** in the re-implementation — see T-WC-17
  for the intrinsic/extrinsic decision.
  - Legacy origin: `CoordinateSystem.py:82-99`
  - Definition of done: a pure 30° rotation about z yields `[0, 0, 30]`; a
    combined rotation is asserted against a hand-computed extrinsic reference so
    the convention is pinned by a test, not by a comment.
  - Confidence: 🟢

- [ ] **T-WC-05 — `CoordinateSystem` serialisation pair.**
  `__getstate__` emits `xDir`, `yDir`, `zDir`, `origin` **and** `euler_xyz`;
  `from_json_dict` defaults each direction to the identity basis and the origin
  to `[0,0,0]`, and **recomputes** `euler_xyz` rather than reading it.
  Plus `from_json(file_path)` / `save_to_json(file_path)` single-object file I/O.
  - Legacy origin: `CoordinateSystem.py:55-63, 101-144`
  - Definition of done: `from_json_dict({})` yields the identity frame; a
    hand-edited `euler_xyz` of `[99,99,99]` on an identity basis loads as
    `[0,0,0]`; a round-trip through `save_to_json` / `from_json` is lossless.
  - Confidence: 🟢

### Spars and workplanes

- [ ] **T-WC-06 — Spar origin/vector resolution.**
  Default `spare_position_factor` to `0.25` when `None`; when `spare_vector` is
  `None`, derive it from the standard origin/vector helper for that segment
  (centred on the camber line); otherwise **normalise** the supplied vector; then,
  independently, derive `spare_origin` when it is `None`.
  - Legacy origin: `aircraft_topology/wing/WingConfiguration.py:354-372`
  - Definition of done: a spar with neither factor nor vector lands on the
    quarter-chord standard vector; a vector of length 3.0 becomes a unit vector
    in the same direction; a spar with an explicit vector but no origin still
    receives the standard origin. See T-WC-15 for the dead branch.
  - Confidence: 🟢

- [ ] **T-WC-07 — Follow-mode spar chaining.**
  `spare_origin = prev_segment.spare_list[idx].spare_origin +
  prev_segment.spare_list[idx].spare_vector * prev_segment.length`.
  - Legacy origin: `WingConfiguration.py:348-352`
  - Definition of done: a two-segment wing with a `follow` spar produces a
    continuous line whose second origin equals the first origin plus the first
    vector scaled by the first segment's length.
  - Confidence: 🟢

- [ ] **T-WC-08 — Per-segment workplane.**
  Select `_get_absolute_segment_coordinate_system` for
  `parameters == "aerosandbox"` and `_get_relative_segment_coordinate_system`
  for `"relative"`; take column 0 as `xDir`, column 2 as `normal` and column 3
  as `origin` from the transposed 4×4 transform, truncating each to three
  components; build a `Plane`; support `ignore_nose_point`; **cache** the result
  per segment.
  - Legacy origin: `WingConfiguration.py:374-400`
  - Definition of done: both parameterisations return a plane whose origin
    matches the segment origin; `ignore_nose_point=True` differs by exactly the
    nose offset; a repeated call for the same segment does not recompute the
    chain. Error message: see T-WC-19.
  - Confidence: 🟢

### Component placement

- [ ] **T-WC-09 — `ComponentInformation`.**
  `(height, width, length: PositiveFloat, rot_x/rot_y/rot_z = 0.0,
  trans_x/trans_y/trans_z = 0.0)`; `get_corner_point()` →
  `gp_Pnt(trans_x, trans_y, trans_z)`; `get_middle_point()` and `get_z_axis()`
  rotating about the **corner point** in **X → Y → Z** order.
  - Legacy origin: `aircraft_topology/components/ComponentInformation.py:8-38`
  - Definition of done: rotating only `rot_z` leaves the x/y corner coordinates
    on the expected circle and z unchanged; the rotation order is asserted with
    a non-commuting combination. See T-WC-16 and T-WC-18 for the two defects.
  - Confidence: 🟢

- [ ] **T-WC-10 — `ServoInformation`.**
  `length` / `width` / `height` as read-only properties backed by `self.servo`,
  with no-op setters; `lever_length`; a default
  `Servo(length, width, height, 0,0,0,0,0,0,0,0)` built **only** when
  `servo is None`; eight precomputed `_corner_vecs`; `super().__init__` called
  with the **resolved** (servo-backed) dimensions.
  - Legacy origin: `components/ServoInformation.py:30-80`
  - Definition of done: `servo_info.height = 99` is provably a no-op; supplying
    both a `servo` and explicit dimensions provably uses the servo's; the eight
    corner vectors match the resolved dimensions.
  - Confidence: 🟢

- [ ] **T-WC-11 — `EngineInformation` and `Position`.**
  `EngineInformation` maps `down_thrust → rot_y` and `side_thrust → rot_z` and
  carries `screw_hole_circle`, `mount_box_length`, `screw_din_diameter`,
  `screw_length`; `Position(x, y, z)` with `get_x/y/z`.
  - Legacy origin: `components/EngineInformation.py:8`;
    `aircraft_topology/Position.py:1`
  - Definition of done: a 3° down-thrust produces `rot_y == 3`; a 2° side-thrust
    produces `rot_z == 2`. (Unit ambiguity is T-WC-18.)
  - Confidence: 🟢

- [ ] **T-WC-12 — `Printer3dSettings`.**
  `layer_height = 0.24`, `wall_thickness = 0.42`,
  `rel_gap_wall_thickness = 0.075`, all `PositiveFloat`, all millimetres.
  - Legacy origin: `aircraft_topology/printer3d/Printer3dSettings.py:4`
  - Definition of done: the defaults match exactly the fallback
    `construction-plans` uses when no `printer_settings` component row exists
    (`construction_plan_service.py:1009-1011`).
  - Confidence: 🟢

### The aircraft aggregate

- [ ] **T-WC-13 — `AirplaneConfiguration` construction and export envelopes.**
  Store `name`, `total_mass` (from `total_mass_kg`), `wings`, `fuselages`;
  resolve the main wing; `to_dict()` emitting `"fuselages"` **only when truthy**;
  `save_to_json` with `indent=4`; `save_to_zip` writing a temporary
  `wings/` + `fuselages/` tree with one JSON per object, then zipping it.
  - Legacy origin: `aircraft_topology/airplane/AirplaneConfiguration.py:21-60`
  - Definition of done: an aircraft without fuselages produces a dict with no
    `"fuselages"` key; the zip contains exactly one file per wing and per
    fuselage; the temporary tree is cleaned up.
  - Confidence: 🟢

- [ ] **T-WC-14 — `asb_airplane` projection.**
  A `cached_property` converting each wing with `scale = mm_to_m_scale = 1.0e-3`
  and each fuselage via `asb_fuselage`, building
  `asb.Airplane(name=…, xyz_ref=None, wings=…, fuselages=…, propulsors=None,
  analysis_specific_options={asb.AVL: {"profile_drag_coefficient": 0.}})`.
  - Legacy origin: `AirplaneConfiguration.py:165-186`
  - Definition of done: a 1000 mm root chord becomes a 1.0 m ASB chord; the AVL
    option is set; the property is computed once. See T-WC-20 for the main-wing
    issue and the `xyz_ref=None` divergence.
  - Confidence: 🟢

### CadQuery extensions

- [ ] **T-WC-21 — Import-time plugin registration.**
  Importing the plugin package must attach `Workplane.fix_shape`, `.offset3D`,
  `.display`, `.sewAndFix`, `.airfoil`, `.wing_root_segment`, `.wing_segment`
  and `Sketch.segmentToEdge`.
  - Legacy origin: `cad_designer/cq_plugins/__init__.py`
  - Definition of done: every listed attribute exists after the import; a test
    asserts the complete set so a silently dropped import is caught.
  - Confidence: 🟢

- [ ] **T-WC-22 — `conditional_execute` gate.**
  Run the decorated function only when the env var is set **and**
  `env_var.upper() in ["1","ON","TRUE","ENABLED"]`; otherwise log
  `"function '<name>' has been called, but has not been executed as '<VAR>' is not set."`
  and **return `self`**.
  - Legacy origin: `cad_designer/decorators/general_decorators.py:5-21`
  - Definition of done: unset / `"0"` / `"yes"` all leave it disabled and return
    the receiver unchanged; `"1"`, `"on"`, `"True"`, `"ENABLED"` all enable it;
    the fluent chain survives the disabled path.
  - Confidence: 🟢

- [ ] **T-WC-23 — `fluent_init` decorator.**
  Attach a static `init()` factory whose introspected signature is the
  constructor's minus `self`; applied to `WingConfiguration` only.
  - Legacy origin: `general_decorators.py:28-39`
  - Definition of done: `WingConfiguration.init(...)` constructs an instance and
    `inspect.signature` on it omits `self`.
  - Confidence: 🟢

### Preservation constraints

> Behaviour to **reproduce**, and defects **not** to carry forward. Nothing here
> authorises editing the legacy files (ADR 0002).

- [ ] **T-WC-15 — REPRODUCE the behaviour, DROP the dead branch.**
  The `0.25` default makes the `elif spare.spare_vector is None:` "perpendicular
  spare" branch unreachable. The **observable behaviour** (quarter-chord standard
  vector) must be reproduced exactly; the unreachable code must not be copied.
  `cad_designer/CLAUDE.md` names this branch explicitly as one that stays in the
  legacy tree.
  - Legacy origin: `WingConfiguration.py:354-372`; `cad_designer/CLAUDE.md`;
    ADR 0002
  - Definition of done: spar origins and vectors are byte-identical to the
    legacy output for the same input; the re-implementation contains no
    unreachable branch; a test documents that a perpendicular spar is **not** a
    supported mode today.
  - Confidence: 🟢

- [ ] **T-WC-16 — DO NOT REPRODUCE: `gp_D*` singleton mutation.**
  `get_z_axis` aliases the module-level `gp_DZ` and calls `Rotate`, which mutates
  in place, permanently corrupting `gp_DX`/`gp_DY`/`gp_DZ` for the process. Copy
  the direction before rotating.
  - Legacy origin: `ComponentInformation.py:4-6, 33-38`
  - Definition of done: calling `get_z_axis()` on two instances with different
    rotations yields the correct axis both times; the module constants are
    unchanged afterwards; a regression test asserts the constants explicitly.
  - Confidence: 🟢

- [ ] **T-WC-17 — RESOLVE: intrinsic vs extrinsic Euler angles.**
  The call site passes `'XYZ'` (intrinsic in SciPy) but the implementation
  lower-cases it to `'xyz'` (extrinsic). `InvalidRotationOrderException` is
  declared and never raised.
  - Legacy origin: `CoordinateSystem.py:7, 53, 98`
  - Definition of done: a human confirms which convention consumers expect;
    the re-implementation states it in the signature and the docstring, validates
    the order argument (or removes it), and pins it with the T-WC-04 test.
  - Confidence: 🟢 — decided (`Q-CT-4`). Note that no consumer of
    `euler_xyz` was identified during analysis, so the blast radius may be zero.

- [ ] **T-WC-18 — RESOLVE: rotation units and the `get_middle_point` z term.**
  `rot_x/rot_y/rot_z` are unlabelled floats passed to `gp_Ax1` rotations, which
  OCCT defines in **radians**, while `EngineInformation`'s
  `down_thrust`/`side_thrust` read naturally as degrees. Separately,
  `get_middle_point` uses `self.length/2` on the **z** term where `height/2`
  reads as intended, with an undocumented `+x`, `−y`, `−z` sign pattern.
  - Legacy origin: `ComponentInformation.py:26-31`;
    `EngineInformation.py:8`
  - Definition of done: a human decision is recorded on (a) the unit and (b)
    whether the z term is a bug; the re-implementation states the unit in the
    signature and the docstring and covers the corner convention with a test.
  - Confidence: 🟢 — decided (`Q-CT-5`). **Previously this blocked any faithful
    reproduction of servo and engine placement.**

- [ ] **T-WC-19 — RESOLVE: `get_wing_workplane`'s error message.**
  It branches on `parameters ∈ {"aerosandbox", "relative"}` but raises
  `"should be 'absolute' or 'relative'"`.
  - Legacy origin: `WingConfiguration.py:389-394`
  - Definition of done: a human confirms whether `"absolute"` was renamed to
    `"aerosandbox"`; the re-implementation's message lists exactly the accepted
    values, and a test asserts the message names only real options.
  - Confidence: 🟢 — decided in the validation interview.

- [ ] **T-WC-20 — DO NOT REPRODUCE: `_main_wing_index = 0` and the bare
  `IndexError`.**
  Select the main wing the way gh-788 fixed it in the app converter — largest
  planform — not by position. Also decide whether an empty `wings` list should
  raise a domain error rather than a bare `IndexError`, and whether
  `xyz_ref=None` is intentional (the app's own converter sets it explicitly).
  - Legacy origin: `AirplaneConfiguration.py:31-32, 165-186`;
    `app/converters/model_schema_converters.py:761-817`
  - Definition of done: a tail-first aircraft resolves the same main wing as
    `aeroplane_schema_to_asb_airplane`; an empty `wings` list produces a clear
    validation error; a regression test covers the ≈8× reference-area error the
    positional choice produced.
  - Confidence: 🟢 (main wing) / 🔴 (the `xyz_ref` question)

- [ ] **T-WC-24 — DO NOT REPRODUCE: the unwired `scaleXyz` plugin and its
  siblings.**
  `cq_plugins/scaleXyz` is never imported (so `Workplane.scaleXyz` never exists)
  and has a typo'd parameter `y_sacle`; the package ships a stale
  `offest3D/.ipynb_checkpoints/` copy; the plugin directory itself is misspelled
  `offest3D`.
  - Legacy origin: `cq_plugins/__init__.py`; `cq_plugins/scaleXyz/scaleXyz.py:6`
  - Definition of done: the re-implementation has no unregistered plugin; the
    directory names are spelled correctly; each omission is listed in the
    migration notes.
  - Confidence: 🟢

- [ ] **T-WC-25 — RESOLVE: `CoordinateSystem` mutability and `ServoInformation`
  staleness.**
  `euler_xyz` is derived once and never recomputed, so mutating a direction
  vector afterwards leaves the two inconsistent; `_corner_vecs` are frozen at
  construction and go stale if the backing `Servo` changes.
  - Legacy origin: `CoordinateSystem.py:48-53`; `ServoInformation.py:55-70`
  - Definition of done: a decision on whether these objects are immutable value
    objects (preferred — make them frozen) or mutable entities (then the derived
    values must be recomputed on read).
  - Confidence: 🟡

## Test Tasks

- [ ] **TT-WC-01 — Happy path:** an identity `CoordinateSystem` yields
      `euler_xyz == [0,0,0]` and round-trips through `__getstate__` /
      `from_json_dict`.
- [ ] **TT-WC-02 — Failure:** non-orthogonal and mirrored (`det = −1`) bases both
      raise `InvalidRotationMatrixException`.
- [ ] **TT-WC-03 — Tolerance boundary:** a basis off by `5e-7` is accepted and
      one off by `5e-5` is rejected.
- [ ] **TT-WC-04 — Euler convention pinned:** a non-commuting rotation is
      asserted against a hand-computed extrinsic reference (T-WC-17).
- [ ] **TT-WC-05 — `euler_xyz` ignored on load:** `[99,99,99]` on an identity
      basis loads as `[0,0,0]`.
- [ ] **TT-WC-06 — Load defaults:** `from_json_dict({})` yields the identity
      frame.
- [ ] **TT-WC-07 — Spar defaults:** no factor, no vector, no origin ⇒ factor
      `0.25` plus the standard vector and origin.
- [ ] **TT-WC-08 — Spar vector normalisation:** length 3.0 ⇒ length 1.0, same
      direction.
- [ ] **TT-WC-09 — Spar origin independence:** an explicit vector with no origin
      still receives the standard origin.
- [ ] **TT-WC-10 — Follow-mode chaining:** the second origin equals the first
      origin plus the first vector times the first segment's length.
- [ ] **TT-WC-11 — Workplane parameterisations:** both `"aerosandbox"` and
      `"relative"` return a plane; an unknown value raises `ValueError`.
- [ ] **TT-WC-12 — `ignore_nose_point`:** the two origins differ by exactly the
      nose offset.
- [ ] **TT-WC-13 — Workplane caching:** a repeated call for the same segment does
      not recompute the transform chain.
- [ ] **TT-WC-14 — Rotation order:** a non-commuting `rot_x`/`rot_y` combination
      distinguishes X→Y→Z from Z→Y→X.
- [ ] **TT-WC-15 — `gp_D*` unchanged** after repeated `get_z_axis` calls
      (T-WC-16's regression test).
- [ ] **TT-WC-16 — Servo no-op setters:** assigning to `height`, `width` or
      `length` changes nothing.
- [ ] **TT-WC-17 — Servo dimension precedence:** supplying both a `servo` and
      explicit dimensions uses the servo's.
- [ ] **TT-WC-18 — Servo corner vectors** match the resolved dimensions.
- [ ] **TT-WC-19 — Engine thrust mapping:** `down_thrust → rot_y`,
      `side_thrust → rot_z`.
- [ ] **TT-WC-20 — Printer defaults** match `construction-plans`' fallback triple
      exactly.
- [ ] **TT-WC-21 — Empty wings rejected** at `AirplaneConfiguration`
      construction, with the agreed error type (T-WC-20).
- [ ] **TT-WC-22 — `to_dict` omits `"fuselages"`** when there are none, and
      includes it when there are.
- [ ] **TT-WC-23 — `save_to_zip` contents:** one JSON per wing and per fuselage;
      the temp tree is cleaned up.
- [ ] **TT-WC-24 — ASB scale:** a 1000 mm chord becomes 1.0 m; the AVL
      `profile_drag_coefficient` option is set; the property is computed once.
- [ ] **TT-WC-25 — Main-wing selection:** a tail-first aircraft resolves the same
      main wing as the app converter (T-WC-20).
- [ ] **TT-WC-26 — Literal case normalisation:** `"Root"`→`"root"`,
      `"both"`→`"BOTH"`, non-string rejected at the `Literal` check.
- [ ] **TT-WC-27 — Bounds:** `Factor = 1.5` and `DihedralInDegrees = -200` are
      rejected.
- [ ] **TT-WC-28 — Plugin registration:** the complete documented attribute set
      exists after import.
- [ ] **TT-WC-29 — Display gate matrix:** unset / `"1"` / `"on"` / `"True"` /
      `"ENABLED"` / `"0"` / `"yes"`, asserting `self` is returned when disabled.
- [ ] **TT-WC-30 — `fluent_init`:** `.init()` constructs and its signature omits
      `self`.

## Suggested Order

1. **T-WC-01** first — the literal types appear in the signatures of everything
   else in the slice.
2. **T-WC-02 → T-WC-05** next. `CoordinateSystem` is self-contained and is the
   foundation of the transform chain. T-WC-03 blocks T-WC-04 (validation runs
   before decomposition), and **T-WC-17 must be raised with the maintainer here**,
   before the convention is baked into tests.
3. **T-WC-09 → T-WC-12** — the placement classes, parallelisable with step 2.
   **T-WC-18 is a hard blocker on T-WC-09 and T-WC-11**: the rotation unit must be
   decided before component placement can be reproduced faithfully. T-WC-16 is
   implemented as part of T-WC-09, not bolted on afterwards.
4. **T-WC-06 → T-WC-08** — spars and workplanes. These need the wing topology
   classes from [`wing-design`](../../wing-design/tasks.md); coordinate rather
   than duplicating. T-WC-08 blocks nothing else here but is a prerequisite for
   every wing Creator. T-WC-15 is a review gate on T-WC-06, and T-WC-19 should be
   raised alongside T-WC-08.
5. **T-WC-21 → T-WC-23** — the CadQuery extensions. T-WC-21 must land before any
   Creator that calls `sewAndFix` or `airfoil`; T-WC-22 is a prerequisite for
   `construction-plans`' SSE streaming, so its accepted-value set must not drift.
6. **T-WC-13 → T-WC-14** last — the aggregate depends on the wing and fuselage
   configurations existing. T-WC-20 is a review gate on both, and the
   `xyz_ref=None` question should be settled with `aero-analysis` rather than in
   isolation.
7. **T-WC-24 → T-WC-25** as cleanup and review gates throughout, not as a phase.

## Pending Gaps

- **Are `rot_x`/`rot_y`/`rot_z` degrees or radians?** They are unlabelled floats
  fed to `gp_Ax1` rotations, which OCCT defines in radians, while
  `down_thrust`/`side_thrust` read naturally as degrees. **This blocks faithful
  reproduction of servo and engine placement** — it is the highest-priority
  question in this slice.
- **Is the `self.length/2` z term in `get_middle_point` a bug?** `height/2`
  reads as intended, and the `+x`, `−y`, `−z` sign pattern is undocumented.
- **Should `euler_xyz` be intrinsic or extrinsic?** The caller requests `'XYZ'`
  and the implementation silently lower-cases it. No consumer of `euler_xyz` was
  identified during analysis, so the blast radius may be zero — but that needs
  confirming before the convention is pinned.
- **Why is `InvalidRotationOrderException` declared and never raised?** Either
  order validation was intended and never written, or the exception is dead.
- **Was `"absolute"` renamed to `"aerosandbox"`?** `get_wing_workplane`'s error
  message names a value the code never accepts.
- **Is `AirplaneConfiguration.asb_airplane` a dead path to delete or a second
  entry point to fix?** It carries the gh-788 positional main-wing assumption and
  passes `xyz_ref=None` where the app's converter sets it explicitly — so the two
  ASB paths are not interchangeable even if the main-wing bug were fixed.
- **Should an empty `wings` list be a domain error?** Today it is a bare
  `IndexError` at construction, unmapped by any caller and surfacing as a 500.
  This is the same question `aeroplane-core` raises as
  *"Is an empty `AirplaneConfiguration` legal?"* — and the answer here is that it
  is not constructible at all, which that module's spec should record.
- **Are `CoordinateSystem` and `ServoInformation` value objects or entities?**
  Both derive values at construction (`euler_xyz`, `_corner_vecs`) and never
  recompute them, so post-construction mutation silently desynchronises them.
