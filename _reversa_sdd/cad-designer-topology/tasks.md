# cad-designer-topology — Implementation Tasks

> Executable sequence to re-implement the module from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
> Slice-level task lists:
> [`creator-execution-model/tasks.md`](creator-execution-model/tasks.md),
> [`wingconfiguration-coordinate-system/tasks.md`](wingconfiguration-coordinate-system/tasks.md),
> [`json-polymorphic-roundtrip/tasks.md`](json-polymorphic-roundtrip/tasks.md).
>
> ⚠ **This module is FROZEN in the legacy system (ADR 0002).** These tasks
> describe **what a re-implementation must reproduce**, not edits to make in
> `cad_designer/`. Nothing here authorises modifying the existing files. The
> `### Preservation constraints` section separates behaviour that must be
> carried forward from defects that must not.

## Prerequisites

- [ ] CadQuery / OCCT available — `Workplane` appears in the Creator contract's
      own type signature, so the module cannot be imported without it
      (ADR 0017; absent on `linux/aarch64`).
- [ ] pydantic v2 — `confloat`, `PositiveFloat`, `NonNegativeFloat`,
      `BeforeValidator` back `types.py` and the component classes.
- [ ] NumPy + SciPy — `CoordinateSystem` validates a rotation matrix and calls
      `scipy.spatial.transform.Rotation.from_matrix(...).as_euler(...)`.
- [ ] AeroSandbox — imported at module scope by `AirplaneConfiguration` and the
      `cad_designer/aerosandbox/` bridge.
- [ ] A decision on the **unit contract**: millimetres inside, metres outside
      (ADR 0001). Every downstream converter depends on it.
- [ ] A decision on the **governance model**: what is frozen, what is open, and
      how it is enforced (ADR 0002 — today by lint/coverage exclusion, not code).

## Tasks

### The Creator contract

- [ ] **T-01 — `AbstractShapeCreator` base class.**
  `__init__(creator_id: CreatorId, shapes_of_interest_keys: list[ShapeId] | None,
  loglevel: int = logging.FATAL)` storing `loglevel` and `creator_id`
  **publicly** and `_shapes_of_interest_keys` **privately**; `identifier`
  property returning `creator_id`; `shapes_of_interest_keys` property;
  abstract `_create_shape(shapes_of_interest, input_shapes, **kwargs) -> dict`.
  - Legacy origin: `cad_designer/airplane/AbstractShapeCreator.py:11-47`
  - Definition of done: a subclass implementing only `_create_shape` is
    constructible and executable; `creator_id` survives a JSON round-trip while
    `_shapes_of_interest_keys` does not.
  - Confidence: 🟢

- [ ] **T-02 — `create_shape` template method.**
  Resolve shapes only when `shapes_of_interest_keys is not None`; lower the
  **root** logger level to `self.loglevel` when it is below the effective level;
  call `_create_shape`; restore the previously effective level; return the
  result.
  - Legacy origin: `AbstractShapeCreator.py:49-61`
  - Definition of done: with `loglevel = DEBUG` and a root at `WARNING`, records
    emitted inside `_create_shape` are captured and the root is back at
    `WARNING` afterwards.
  - Confidence: 🟢

- [ ] **T-03 — Positional slot resolution (`return_needed_shapes`).**
  Raise `KeyError(f'{identifier}: there are less input_shapes than
  shapes_needed.')` when `count(None) > len(input_shapes)`; otherwise replace
  each `None` with a key from `input_shapes.keys().__reversed__()`
  (**most significant last**); look the resolved names up in `kwargs`; return a
  dict in the **declared** order.
  - Legacy origin: `AbstractShapeCreator.py:79-95`
  - Definition of done: `[None]` against `{"a":…, "b":…}` resolves to `b`;
    `[None, None]` against a single input raises before any lookup; a mixed
    `["a", None]` resolves the named key from the registry and the slot from the
    inputs.
  - Confidence: 🟢

- [ ] **T-04 — Registry availability check.**
  `check_if_shapes_are_available` returns `{}` for a `None` list, otherwise
  collects the present keys and raises
  `KeyError(f"shapes are missing in step '{identifier}': {missing}")`.
  - Legacy origin: `AbstractShapeCreator.py:63-77`
  - Definition of done: the error names the step and every missing key; a test
    documents that the ordering of names in the message is not stable (a `set`
    is used internally).
  - Confidence: 🟢

- [ ] **T-05 — Output-key convention and collision semantics.**
  `<identifier>` for a single shape, `<identifier>.<known_name>` for named
  outputs, `<identifier>[i]` for indexed ones; a repeated identifier silently
  overwrites the earlier shape.
  - Legacy origin: `AbstractShapeCreator.py:20-27, 43-46`
  - Definition of done: a creator returning two named shapes produces exactly
    two dotted keys; a test documents the overwrite rather than asserting an
    error.
  - Confidence: 🟢

- [ ] **T-06 — The Creator authoring contract.**
  `suggested_creator_id` class attribute (may contain `{param}` placeholders);
  first docstring line = catalogue description; an `Attributes:` block of
  `name (type): text` lines = per-parameter tooltips; runtime-injected config
  stored as `self._private`; `loglevel` default `logging.INFO` in new Creators
  (the base class defaults to `FATAL`); registration in the subpackage
  `__init__.py` is mandatory for decodability.
  - Legacy origin: `cad_designer/airplane/creator/_creator_template.py:1-111`
  - Definition of done: a Creator written from the template appears in the
    catalogue with a description and per-parameter tooltips, and decodes from a
    stored plan.
  - Confidence: 🟢

- [ ] **T-07 — The 29-Creator inventory across five packages.**
  `cad_operations/` (9), `wing/` (3), `fuselage/` (9), `export_import/` (6),
  `components/` (2), each re-exported from its subpackage `__init__.py`, with
  `creator/__init__.py` star-importing all five.
  - Legacy origin: `cad_designer/airplane/creator/*/__init__.py`;
    full list in [`design.md`](design.md) §Creator inventory
  - Definition of done: `from cad_designer.airplane.creator import *` exposes
    every class named in the inventory table, and a test asserts the count.
  - Confidence: 🟢

### The construction tree

- [ ] **T-08 — `ConstructionStepNode` as Creator + `MutableMapping`.**
  `__init__(creator, successors: OrderedDict = None, **kwargs)` calling
  `super().__init__(f"{creator.identifier}", shapes_of_interest_keys=None)`;
  `__getitem__/__setitem__/__delitem__/__len__/__iter__` over `successors`;
  `append(value)` keyed by `value.creator.identifier`.
  - Legacy origin: `cad_designer/airplane/ConstructionStepNode.py:12-46`
  - Definition of done: the node's `identifier` equals its creator's; the node
    never invokes `return_needed_shapes` on its own behalf.
  - Confidence: 🟢

- [ ] **T-09 — `ConstructionStepNode._create_shape` traversal.**
  Call the creator; build `_input_shapes` as `{}` when `input_shapes is None`
  else a **copy**; pop every key the creator just produced; update with the
  outputs so they land **last**; `kwargs.update(output_shapes)`; recurse into
  every successor with `_input_shapes`; return `kwargs`.
  - Legacy origin: `ConstructionStepNode.py:48-76`
  - Definition of done: a re-created key appears exactly once and last in the
    child's `input_shapes`; the caller's dict is provably unmutated; the return
    value contains every shape from every descendant.
  - Confidence: 🟢

- [ ] **T-10 — `ConstructionRootNode` branch isolation.**
  Identifier `f"{creator_id}.root"`; `_output_shapes = None` (private);
  `_create_shape` hands **every** top-level successor `input_shapes={}` and
  threads only `kwargs`.
  - Legacy origin: `cad_designer/airplane/ConstructionRootNode.py:18-58`
  - Definition of done: a positional slot in the second top-level branch raises
    `KeyError` even though the first branch produced shapes; a named reference
    across branches resolves.
  - Confidence: 🟢

- [ ] **T-11 — `JSONStepNode` eager sub-tree loading.**
  Store `json_file_path` publicly and the injection payload as
  `_to_be_injected`; decode the file with `GeneralJSONDecoder(**kwargs)` at
  construction; pop `successors` and `creator` from `kwargs`; adopt the decoded
  node's `creator` and `successors`.
  - Legacy origin: `cad_designer/airplane/JSONStepNode.py:4-24`
  - Definition of done: the node behaves identically to the sub-tree written
    inline; all runtime config must be supplied when the node is **built**, and
    a test documents that.
  - Confidence: 🟢

### Serialisation

- [ ] **T-12 — `GeneralJSONEncoder`.**
  `JSON_CLASS_TYPE_ID = "$TYPE"`; emit
  `{k: v for k, v in o.__dict__.items() if not k.startswith('_')}` plus
  `"$TYPE" = o.__class__.__name__`.
  - Legacy origin: `cad_designer/airplane/GeneralJSONEncoderDecoder.py:13-25`
  - Definition of done: a creator holding `self._config` round-trips with no
    underscore-prefixed key in the JSON; `ConstructionRootNode._output_shapes`
    and `JSONStepNode._to_be_injected` are absent.
  - Confidence: 🟢

- [ ] **T-13 — `$TYPE` class resolution.**
  `getattr(sys.modules["cad_designer.airplane.GeneralJSONEncoderDecoder"],
  dic["$TYPE"])`, with the module importing `ConstructionRootNode`,
  `ConstructionStepNode`, `from cad_designer.airplane.creator import *` and
  `cad_designer.cq_plugins`.
  - Legacy origin: `GeneralJSONEncoderDecoder.py:1-7, 193-198`
  - Definition of done: every registered Creator decodes; an unregistered one
    raises `AttributeError`; a test asserts that no topology class is
    resolvable.
  - Confidence: 🟢

- [ ] **T-14 — Parameter selection, `**kwargs` branch vs. intersection branch.**
  When `"kwargs" in inspect.signature(cls.__init__).parameters`: pass the whole
  dict plus **all** decoder kwargs. Otherwise: intersect the dict with the
  `__init__` parameter names and overlay the matching decoder kwargs (injections
  win).
  - Legacy origin: `GeneralJSONEncoderDecoder.py:199-210`
  - Definition of done: a Creator with `**kwargs` receives `wing_config`; one
    without receives only its declared parameters; a stored key the constructor
    does not declare is dropped rather than raising `TypeError`.
  - Confidence: 🟢

- [ ] **T-15 — Type coercion (`_coerce_params` + `_resolve_base_type`).**
  Read `cls.__init__.__annotations__` (minus `return`); pass through `None`
  values and unannotated keys; unwrap `NewType.__supertype__`, `Annotated`,
  `confloat`, and **string** annotations from
  `from __future__ import annotations`; coerce `float`/`int`/`bool`/`str`; on
  `ValueError`/`TypeError` log
  `"Type coercion failed for %s.%s: value=%r, expected=%s (%s)"` and keep the raw
  value.
  - Legacy origin: `GeneralJSONEncoderDecoder.py:28-84, 125-176`
  - Definition of done: `"0.1"` → `0.1` for a `float` parameter; `"abc"` on a
    `float` logs a warning and survives as `"abc"`; a `NewType`-annotated
    parameter coerces to its supertype.
  - Confidence: 🟢

- [ ] **T-16 — Locale-aware numeric normalisation.**
  `"0,1"` → `0.1`; `"1.234,56"` → `1234.56`; `"1,234.56"` → `1234.56`;
  `"1234"` unchanged. The **last** separator present decides which is the
  decimal mark.
  - Legacy origin: `_normalize_numeric_string`, `GeneralJSONEncoderDecoder.py:95-122`
  - Definition of done: all four documented cases are covered by a table test,
    plus a whitespace-padded input.
  - Confidence: 🟢

- [ ] **T-17 — The `list[...]`-from-string guard.**
  When the annotation is a list type and the value is a `str`, wrap it into a
  one-element list (`[]` for an empty/whitespace string); when the annotation is
  a list type and the value is neither list nor str, pass through. This check
  **must run before** `_resolve_base_type`.
  - Legacy origin: `GeneralJSONEncoderDecoder.py:144-152`; `_is_list_type` l.87-92
  - Definition of done: `"fuselage"` on a `list[ShapeId]` parameter yields
    `["fuselage"]`, never a list of characters; a test documents that reordering
    the guard after `_resolve_base_type` would stringify the list.
  - Confidence: 🟢

- [ ] **T-18 — `creator_id` placeholder substitution.**
  `re.sub(r"\{(\w+)\}", …)` over the **already-coerced** sibling values; a value
  that is missing, `None`, a `dict` or a `list` leaves the placeholder verbatim.
  - Legacy origin: `GeneralJSONEncoderDecoder.py:212-223`
  - Definition of done: `"{wing_index}.loft"` with `wing_index = "main"` yields
    `"main.loft"`; `"{missing}.loft"` is unchanged; a `list`-valued parameter
    does not interpolate.
  - Confidence: 🟢

- [ ] **T-19 — The decoder's own kwargs split.**
  `GeneralJSONDecoder.__init__` must separate the arguments `JSONDecoder`
  accepts from the payload injected into decoded objects, forwarding only the
  former to `JSONDecoder.__init__`.
  - Legacy origin: `GeneralJSONEncoderDecoder.py:180-191`
  - Definition of done: passing both `object_pairs_hook` and `wing_config`
    works; `wing_config` reaches the Creators and never reaches `JSONDecoder`.
  - Confidence: 🟢

- [ ] **T-20 — The second, marker-less topology format.**
  `__getstate__() -> dict` plus `@staticmethod from_json_dict(data) -> Self` on
  `WingConfiguration`, `WingSegment`, `Airfoil`, `Spare`,
  `TrailingEdgeDevice`, `Turbulator`, `Servo`, `CoordinateSystem`,
  `AirplaneConfiguration`, `FuselageConfiguration` — with **no** `$TYPE` key.
  Topology objects enter a running plan only as decoder kwargs.
  - Legacy origin: `code-analysis.md` §A second, independent serialisation
    system; `CoordinateSystem.py:55-63, 101-117`;
    `AirplaneConfiguration.py:34-46`
  - Definition of done: a `WingConfiguration` round-trips through the pair; a
    test asserts that no serialised topology dict contains `$TYPE` and that no
    stored plan contains a topology object.
  - Confidence: 🟢

- [ ] **T-21 — `AirplaneConfiguration` export envelopes.**
  `to_dict()` → `{"name", "total_mass_kg", "wings": [...]}` plus `"fuselages"`
  only when truthy; `save_to_json` with `indent=4`; `save_to_zip` writing a
  temporary `wings/` + `fuselages/` tree, one JSON per object, then zipping it.
  - Legacy origin: `AirplaneConfiguration.py:34-60`
  - Definition of done: an aircraft with no fuselages produces a dict without a
    `"fuselages"` key; the zip contains one file per wing and per fuselage.
  - Confidence: 🟢

### Domain types and geometry classes

- [ ] **T-22 — Domain literal types with case normalisation.**
  `Factor = confloat(ge=0, le=1.0)`;
  `DihedralInDegrees = confloat(ge=-180.0, le=180.0)`;
  `CoordinateSystemBase`, `WingSegmentType`, `TipType` lower-cased by a
  `BeforeValidator`; `WingSides` **upper**-cased; `ShapeId` / `CreatorId` as
  `NewType(..., str)`.
  - Legacy origin: `cad_designer/airplane/types.py:5-38`
  - Definition of done: `"Root"` validates to `"root"`, `"both"` validates to
    `"BOTH"`, and a non-string input passes through the validator untouched.
  - Confidence: 🟢

- [ ] **T-23 — `CoordinateSystem` construction and validation.**
  Store `xDir/yDir/zDir/origin` as lists; build `R = matrix([xDir,yDir,zDir]).T`;
  require `R·Rᵀ ≈ I` **and** `det R ≈ 1` (`atol=1e-6`) or raise
  `InvalidRotationMatrixException`; derive `euler_xyz` in degrees.
  `from_json_dict` defaults to the identity basis and origin `[0,0,0]` and
  **recomputes** `euler_xyz` rather than reading it.
  - Legacy origin: `cad_designer/airplane/aircraft_topology/wing/CoordinateSystem.py:29-117`
  - Definition of done: a non-orthonormal basis raises; a mirrored basis
    (`det = −1`) raises; a hand-edited `euler_xyz` in the JSON is provably
    ignored.
  - Confidence: 🟢

- [ ] **T-24 — Spar origin/vector resolution in `WingConfiguration`.**
  Default `spare_position_factor` to `0.25` when `None`; when `spare_vector` is
  `None`, derive it from `_get_standard_spare_origin_and_vector` for that
  segment; otherwise normalise the supplied vector; when `spare_origin` is
  `None`, derive it the same way. Cross-reference
  [`wing-design`](../wing-design/design.md) §F5 for the **consumers**
  (`should_preserve_normal_spare`, `_recompute_spare_vectors`) — they are not
  this module's responsibility.
  - Legacy origin: `WingConfiguration.py:354-372`
  - Definition of done: a spar with neither factor nor vector lands on the
    quarter-chord standard vector; a supplied vector is normalised, not
    replaced.
  - Confidence: 🟢

- [ ] **T-25 — `ComponentInformation` and its subclasses.**
  `ComponentInformation(height, width, length, rot_*, trans_*)` with
  `get_corner_point`, `get_middle_point`, `get_z_axis` rotating about the corner
  point in **X → Y → Z** order. `ServoInformation` exposes `length/width/height`
  as read-only properties backed by `self.servo` (setters are no-ops) and builds
  a default `Servo` only when none is supplied. `EngineInformation` maps
  `down_thrust → rot_y` and `side_thrust → rot_z`.
  `Printer3dSettings(0.24, 0.42, 0.075)`.
  - Legacy origin: `components/ComponentInformation.py:8-38`;
    `components/ServoInformation.py:30-80`; `components/EngineInformation.py:8`;
    `printer3d/Printer3dSettings.py:4`
  - Definition of done: writing `servo_info.height = 99` is provably a no-op;
    supplying both a `servo` and explicit dimensions provably ignores the
    dimensions; rotation order is asserted.
  - Confidence: 🟢

- [ ] **T-26 — `AirplaneConfiguration` construction and ASB conversion.**
  Store `name`, `total_mass`, `wings`, `fuselages`; resolve `_main_wing` from
  `_main_wing_index`; `asb_airplane` as a `cached_property` converting at
  `mm_to_m_scale = 1.0e-3` with
  `analysis_specific_options = {asb.AVL: {"profile_drag_coefficient": 0.0}}`.
  - Legacy origin: `AirplaneConfiguration.py:21-32, 165-186`
  - Definition of done: a 1000 mm chord becomes a 1.0 m ASB chord; an empty
    `wings` list raises `IndexError` at construction (documented, see T-31).
  - Confidence: 🟢

### CadQuery extensions

- [ ] **T-27 — Import-time plugin registration.**
  Importing the plugin package must attach `Workplane.fix_shape`, `.offset3D`,
  `.display`, `.sewAndFix`, `.airfoil`, `.wing_root_segment`, `.wing_segment`
  and `Sketch.segmentToEdge`. The serialisation module must perform that import
  so that decoding a plan guarantees the extensions exist.
  - Legacy origin: `cad_designer/cq_plugins/__init__.py`;
    `GeneralJSONEncoderDecoder.py:7`
  - Definition of done: after `import …cq_plugins`, every listed attribute is
    present; a test asserts the decoder module triggers it transitively.
  - Confidence: 🟢

- [ ] **T-28 — `conditional_execute` gate.**
  Run the decorated function only when the env var is set and its
  `.upper()` is in `["1","ON","TRUE","ENABLED"]`; otherwise log
  `"function '<name>' has been called, but has not been executed as '<VAR>' is not set."`
  and **return `self`** so the fluent chain survives.
  - Legacy origin: `cad_designer/decorators/general_decorators.py:5-21`
  - Definition of done: `display()` with the var unset returns the same
    workplane and logs once; `"on"`, `"True"` and `"1"` all enable it; `"0"` and
    `"yes"` do not.
  - Confidence: 🟢

- [ ] **T-29 — `fluent_init` decorator.**
  Attach a static `init()` factory carrying the constructor's signature minus
  `self`; applied to `WingConfiguration` only.
  - Legacy origin: `general_decorators.py:28-39`
  - Definition of done: `WingConfiguration.init(...)` constructs an instance and
    its introspected signature omits `self`.
  - Confidence: 🟢

### Preservation constraints

> Behaviour that a faithful re-implementation must **reproduce**, and defects it
> must **not** carry forward. In the legacy system none of these are to be fixed
> in place (ADR 0002).

- [ ] **T-30 — REPRODUCE: the `0.25` `spare_position_factor` default and the
  unreachable perpendicular-spare branch.**
  The default makes the second condition of the first `if` always true, which
  makes the `elif spare.spare_vector is None:` branch dead. Downstream geometry
  depends on the observable behaviour (quarter-chord standard vector), so the
  **behaviour** must be reproduced; the dead branch itself must be dropped, not
  copied.
  - Legacy origin: `WingConfiguration.py:354-372`; `cad_designer/CLAUDE.md`;
    ADR 0002
  - Definition of done: the re-implementation produces byte-identical spar
    origins/vectors for the same input, with no unreachable code and a test
    documenting that a perpendicular spar is **not** a supported mode today.
  - Confidence: 🟢

- [ ] **T-31 — DO NOT REPRODUCE: `gp_D*` singleton mutation.**
  `get_z_axis` does `z = gp_DZ` (an alias) then `z.Rotate(...)`, and
  `gp_Dir.Rotate` mutates in place, permanently corrupting the module-level
  `gp_DX`/`gp_DY`/`gp_DZ`. A re-implementation must copy the direction before
  rotating.
  - Legacy origin: `ComponentInformation.py:4-6, 33-38`
  - Definition of done: calling `get_z_axis()` twice on two instances with
    different rotations yields the correct axis both times, and the module
    constants are unchanged afterwards.
  - Confidence: 🟢

- [ ] **T-32 — RESOLVE: the `get_middle_point` z term and the rotation unit.**
  The z component uses `self.length/2` where `height/2` reads as intended, and
  the sign pattern is `+x`, `−y`, `−z`. `rot_x/rot_y/rot_z` are unlabelled
  floats fed to `gp_Ax1` rotations, which OCCT defines in **radians**.
  - Legacy origin: `ComponentInformation.py:26-31`
  - Definition of done: a human decision is recorded on (a) whether the z term
    is a bug and (b) whether `rot_*` are degrees or radians; the
    re-implementation states the unit in the signature and the docstring.
  - Confidence: 🟢 — decided in the validation interview.

- [ ] **T-33 — DO NOT REPRODUCE: `AirplaneConfiguration._main_wing_index = 0`.**
  The main wing must be selected the way gh-788 fixed it in the app converter —
  largest planform — not by position.
  - Legacy origin: `AirplaneConfiguration.py:31-32`;
    `app/converters/model_schema_converters.py:761-817`
  - Definition of done: a tail-first aircraft resolves the same main wing as
    `aeroplane_schema_to_asb_airplane`; a regression test covers the ≈8×
    reference-area error the positional choice produced.
  - Confidence: 🟢

- [ ] **T-34 — DO NOT REPRODUCE: the non-exception-safe log-level restore.**
  `create_shape` restores the root level on the normal path only, so a raising
  step leaves the process logger permanently lowered. Use `try/finally`.
  - Legacy origin: `AbstractShapeCreator.py:57-61`
  - Definition of done: a `_create_shape` that raises still restores the
    previous root level.
  - Confidence: 🟢

- [ ] **T-35 — RESOLVE: process-global state under concurrency.**
  The root logger level, the `DISPLAY_CONSTRUCTION_STEP` gate and the display
  callback are all process-global, so two concurrent executions interfere. This
  is the same tension ADR 0005 records between `cad-generation`'s process pool
  and `construction-plans`' in-process execution.
  - Legacy origin: `AbstractShapeCreator.py:53-60`;
    `general_decorators.py:14`; ADR 0005
  - Definition of done: a decision is recorded on whether concurrent execution
    in one process is supported; if yes, the log level and the display hook move
    into a per-execution context.
  - Confidence: 🟢 — decided in the validation interview.

- [ ] **T-36 — DO NOT REPRODUCE: dead and unwired code.**
  `AbstractConstructionStep` (abstract, no implementers);
  `create_XYZ_ted_sketch` (defined, absent from the `ted_sketch_creators`
  dispatch); `cq_plugins/scaleXyz` (never imported, and its implementation has a
  typo'd parameter `y_sacle`); the stale `offest3D/.ipynb_checkpoints/` copy;
  the misspelled `offest3D` package name;
  `ConstructionRootNode._output_shapes` (assigned `None`, never written);
  `InvalidRotationOrderException` (declared, never raised).
  - Legacy origin: `AbstractConstructionStep.py:4-11`;
    `creator/wing/ted_sketch_creators.py:22, 187`;
    `cq_plugins/scaleXyz/scaleXyz.py:6`; `cq_plugins/__init__.py`;
    `ConstructionRootNode.py:23`; `CoordinateSystem.py:7`
  - Definition of done: none of these exist in the re-implementation, and each
    is listed in the migration notes so a reviewer can confirm the omission was
    intentional.
  - Confidence: 🟢

- [ ] **T-37 — RESOLVE: `get_wing_workplane`'s error message.**
  It accepts `parameters ∈ {"aerosandbox", "relative"}` but says
  `"should be 'absolute' or 'relative'"`.
  - Legacy origin: `WingConfiguration.py:389-394`
  - Definition of done: a human confirms whether `"absolute"` was renamed to
    `"aerosandbox"`; the re-implementation's message lists exactly the accepted
    values.
  - Confidence: 🟢 — decided in the validation interview.

- [ ] **T-38 — REPRODUCE: governance and the exclusion posture.**
  A re-implementation must decide how the fragile-geometry boundary is enforced.
  Today it is `sonar.exclusions = …,cad_designer/**` plus a ruff
  `extend-exclude`, i.e. ≈22 k LOC neither linted nor measured, with the rule
  living in `cad_designer/CLAUDE.md` rather than in code.
  - Legacy origin: ADR 0002; `sonar-project.properties:10`;
    `pyproject.toml:122-129`
  - Definition of done: the boundary is documented and, ideally, enforced by
    something stronger than a lint exclusion (e.g. an import-linter contract or
    a package boundary test).
  - Confidence: 🟡 INFERRED — the *need* is confirmed; the mechanism is a
    design choice.

## Test Tasks

- [ ] **TT-01 — Happy path:** a two-branch tree encodes, decodes and executes,
      producing the same shape keys as the in-memory original.
- [ ] **TT-02 — Failure:** a `$TYPE` naming a class that does not exist raises
      `AttributeError` at decode time.
- [ ] **TT-03 — Positional resolution matrix:** `[None]` / `[None, None]` /
      `["a", None]` against 0, 1 and 2 input shapes — including the
      "less input_shapes than shapes_needed" raise.
- [ ] **TT-04 — Ordering invariant:** a re-created key appears once and last in
      the child's `input_shapes`; removing the pop loop changes which shape a
      positional slot resolves to (a documented regression test).
- [ ] **TT-05 — Non-mutation:** the caller's `input_shapes` dict is identical
      before and after a step executes.
- [ ] **TT-06 — Branch isolation:** a positional slot in a second top-level
      branch raises even though the first branch produced shapes; a named
      reference across branches succeeds.
- [ ] **TT-07 — Missing shape:** the `KeyError` names the step identifier and
      the missing key.
- [ ] **TT-08 — Privacy of serialisation:** no key starting with `_` appears in
      the encoded JSON, for each of `AbstractShapeCreator` subclass,
      `ConstructionRootNode` and `JSONStepNode`.
- [ ] **TT-09 — `**kwargs` vs. intersection decode:** a Creator with `**kwargs`
      receives injected config; one without receives only declared parameters;
      an unknown stored key is dropped rather than raising `TypeError`.
- [ ] **TT-10 — Coercion table:** `str→float`, `str→int`, `str→bool`,
      `str→str`, `NewType`, `Annotated`, `confloat` and string annotations.
- [ ] **TT-11 — Locale table:** `"0,1"`, `"1.234,56"`, `"1,234.56"`, `"1234"`,
      and a whitespace-padded variant.
- [ ] **TT-12 — Coercion failure is non-fatal:** `"abc"` on a `float` parameter
      logs a warning and the object still constructs with the raw string.
- [ ] **TT-13 — List guard:** `"fuselage"` on a `list[ShapeId]` yields
      `["fuselage"]`; `""` yields `[]`; a real list passes through.
- [ ] **TT-14 — Placeholder matrix:** resolvable, missing, `None`-valued,
      `list`-valued and `dict`-valued parameters.
- [ ] **TT-15 — Topology round-trip:** `__getstate__` → `from_json_dict` for
      each of the ten classes, asserting no `$TYPE` key is emitted.
- [ ] **TT-16 — `euler_xyz` is recomputed:** a hand-edited value in the JSON is
      ignored on load.
- [ ] **TT-17 — Rotation-matrix rejection:** non-orthonormal and mirrored
      (`det = −1`) bases both raise `InvalidRotationMatrixException`.
- [ ] **TT-18 — Case normalisation:** `"Root"`→`"root"`, `"both"`→`"BOTH"`,
      non-string input untouched.
- [ ] **TT-19 — `ServoInformation` no-op setters** and the ignored constructor
      dimensions when a `servo` is supplied.
- [ ] **TT-20 — `gp_D*` singletons are unchanged** after repeated `get_z_axis`
      calls (the T-31 fix).
- [ ] **TT-21 — Log-level restore on exception** (the T-34 fix).
- [ ] **TT-22 — Display gate matrix:** unset / `"1"` / `"on"` / `"TRUE"` /
      `"ENABLED"` / `"0"` / `"yes"`, asserting the return value is `self` when
      disabled.
- [ ] **TT-23 — Plugin registration:** every documented `Workplane` / `Sketch`
      attribute exists after importing the plugin package, and importing the
      decoder module is sufficient.
- [ ] **TT-24 — Creator inventory:** the 29 registered classes are all reachable
      through the star-import, and a Creator omitted from its subpackage
      `__init__.py` fails to decode.
- [ ] **TT-25 — Corpus decodability:** every JSON under
      `components/constructions/` either decodes or is listed in a known-broken
      allowlist (see TM-01).

## Data Migration Tasks

- [ ] **TM-01 — 🟢 **Delete the three undecodable plan JSONs** (`Q-CT-1`, derived from `P-DEAD-0`).**
      `wings.root.json`, `fuselage.root.json` and `full_wing.json` reference nine
      Creator classes that no longer exist: `FullWingLoftShapeCreator`,
      `FullFuselageLoftShapeCreator`, `WingRibCageCreator`,
      `ReinforcementPipesCreator`, `WingOffsetCreator`, `MirrorShapeCreator`,
      `EngineMountPanelShapeCreator`, `CPACSTrailingEdgeDeviceCreator`,
      `CPACSTrailingEdgeDeviceCutOutCreator`, `CPACSServoCutOutCreator`
      (9 of 32 `$TYPE` names). The remaining five files
      (`RV-7.root.json`, `RV-7-wing.root.json`, `eHawk-wing.root.json`,
      `punisher.root.json`, `configurator-test-wing.root.json`) resolve cleanly.
      Nothing under `app/` reads the directory, so this is latent, not live.
      **Decide: delete, migrate to surviving Creators, or archive with a
      README.** Blocked on the ownership question for the `test/` root.
- [ ] **TM-02 — Add a corpus test so this cannot regress silently.** 🟡
      A test that decodes every shipped plan JSON would have caught the drift the
      moment a Creator was renamed. Requires TM-01 to settle the allowlist first.
- [ ] **TM-03 — Stored plans need a schema version.** 🟡 The class name is the only versioning today; `P-DEAD-0` already bit once (nine deleted Creator classes still referenced).
      Today the compatibility contract is the class **name** and nothing else —
      no version field, no registry, no deprecation path. Any rename is a
      breaking change to `construction_plans.tree_json` rows with no migration
      hook. Owned jointly with
      [`construction-plans`](../construction-plans/tasks.md).

## Suggested Order

1. **T-01 → T-05** first. The Creator contract is the module's public API; every
   Creator, both node types and the whole serialisation layer are written against
   it. T-03's ordering semantics must be settled before T-09 can be correct.
2. **T-08 → T-11** next. The tree depends on T-01…T-05 and nothing else. T-09's
   pop-then-update is what makes T-03 meaningful — implement and test them as a
   pair, not separately.
3. **T-12 → T-19** — serialisation. T-13 blocks T-14; T-15 blocks T-16 and T-17;
   T-17 must be *ordered before* T-15's scalar resolution in the implementation,
   which is worth a comment in the code. Independent of T-20…T-26 and
   parallelisable with them.
4. **T-22 → T-26** — the domain types and frozen geometry classes. T-22 blocks
   T-23 (the literal types appear in its signatures). T-24 needs the wing
   topology classes, which are specified in
   [`wing-design`](../wing-design/requirements.md); coordinate with that module
   rather than duplicating.
5. **T-20 → T-21** — the second serialisation system. Depends on T-22…T-26
   existing, and is what `wing-design`'s `/wingconfig` round-trip rides on.
6. **T-06 → T-07** — the authoring contract and the Creator inventory. T-06
   depends on T-01 and on the catalogue reflection rules owned by
   [`construction-plans`](../construction-plans/design.md); T-07 depends on T-13
   (registration is what makes a class decodable).
7. **T-27 → T-29** — CadQuery extensions. T-27 must land before any Creator that
   calls `sewAndFix` or `airfoil`; T-28 is a prerequisite for
   `construction-plans`' SSE streaming.
8. **T-30 → T-38** — the preservation constraints, applied as review gates
   throughout rather than as a final step. T-32, T-35 and T-37 are blocked on
   human decisions and must be raised **before** the corresponding code is
   written, not after.

## Pending Gaps

- **Are `ComponentInformation.rot_x/rot_y/rot_z` degrees or radians?** They are
  unlabelled floats passed to `gp_Ax1` rotations, which OCCT defines in radians.
  Every consumer (servo and engine creators) inherits the ambiguity.
- **Is the `self.length/2` z term in `get_middle_point` a bug?** `height/2`
  reads as intended, and the sign pattern (`+x`, `−y`, `−z`) is undocumented.
  Both need a human answer before the behaviour can be reproduced deliberately.
- **Who owns `components/constructions/*.json` and the `test/` root that
  authored them?** Three of eight files are undecodable; nothing under `app/`
  reads them; the directory is excluded from ruff but not from pytest.
- **Should stored plans carry a schema version?** The class name is the entire
  compatibility contract; there is no registry, no alias table and no
  deprecation path, so any Creator rename silently breaks stored rows.
- **Is `AirplaneConfiguration.asb_airplane` a dead path to delete or a second
  entry point to fix?** It carries the gh-788 positional main-wing assumption.
  If it is ever called, it inherits the bug; if it is not, it is ≈150 lines of
  unreachable ASB code plus a hard AeroSandbox import.
- **Was `"absolute"` renamed to `"aerosandbox"`?** `get_wing_workplane`'s error
  message names a value the code never accepts.
- **Is concurrent plan execution within one process supported?** The root logger
  level, the `gp_D*` singletons and the display gate are all process-global — the
  same unresolved tension ADR 0005 records for the process pool.
- **Should a Creator identifier collision be an error?** Today the later shape
  silently overwrites the earlier one, which in a large tree is indistinguishable
  from a missing step.
- **Is `_resolve_base_type`'s string heuristic acceptable?** Any annotation
  string containing `"factor"` is coerced to `float`, regardless of the
  parameter's actual type.
