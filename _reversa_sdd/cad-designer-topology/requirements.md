# cad-designer-topology

> Module-level specification. Focuses on WHAT the module does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: cad-designer-topology,
> `_reversa_sdd/data-dictionary.md` §Module: cad-designer-topology,
> `_reversa_sdd/domain.md` §2.10, [ADR 0002](../adrs/0002-cad-designer-is-frozen-new-creators-only.md),
> [ADR 0001](../adrs/0001-millimetres-in-cad-metres-in-db-and-aerosandbox.md).
>
> ⚠ **This module is FROZEN (ADR 0002). The spec documents behaviour to
> preserve, not code to change.** Its failure mode is *silent wrongness, not an
> exception*: a plausible-looking cleanup can change the geometry that comes out
> of a loft without any test failing.

## Overview

`cad-designer-topology` is the `cad_designer/` CadQuery library — the only thing
in the system that turns a parametric aircraft description into a manufacturable
solid. It owns four things: the **frozen topology classes** that describe an
aircraft in millimetres, the **Creator hierarchy** that turns them into shapes,
the **construction-step tree** that sequences Creators, and the **`$TYPE` JSON
serialisation contract** that lets a tree be stored and replayed. It exposes no
HTTP surface — every consumer calls it in-process. 🟢

## Responsibilities

- Define the aircraft topology in a **millimetre, wing-local frame**: `Airfoil`,
  `WingSegment`, `WingConfiguration`, `Spare`, `TrailingEdgeDevice`,
  `Turbulator`, `CoordinateSystem`, `Servo`, `FuselageConfiguration`,
  `AirplaneConfiguration`. 🟢
- Define the **Creator contract** (`AbstractShapeCreator`): a template method,
  a positional/named upstream-shape resolution protocol, and an output-key
  naming convention. 🟢
- Provide **29 registered Creators** across five categories that build wings,
  fuselages, boolean operations, component imports and file exports. 🟢
- Execute a **construction tree** (`ConstructionRootNode` / `ConstructionStepNode`
  / `JSONStepNode`) depth-first, threading a growing shape registry through
  `kwargs`. 🟢
- Serialise and deserialise that tree through the **`$TYPE` dialect**
  (`GeneralJSONEncoder` / `GeneralJSONDecoder`), including type coercion,
  locale-aware numeric normalisation and `{placeholder}` substitution. 🟢
- Provide a **second, independent, marker-less serialisation system**
  (`__getstate__` / `from_json_dict`) for topology objects. 🟢
- Monkey-patch CadQuery with the geometry helpers the Creators rely on
  (`cq_plugins`), including the env-gated `Workplane.display` hook that the
  streaming plan executor toggles. 🟢
- Host `airplane/geometry/**` — **editable feature code**, not frozen topology —
  as the seam between CAD-free decision logic and real lofted geometry. 🟢

**Explicitly NOT this module's responsibility:** the spar sizing / solver /
section-geometry pipeline (→ [`wing-design`](../wing-design/requirements.md),
which owns the formulas even though the files live here), the fuselage slicer
internals (→ [`fuselage-design`](../fuselage-design/requirements.md)), plan CRUD,
execution orchestration, artefact capture and the Creator Catalog REST
projection (→ [`construction-plans`](../construction-plans/requirements.md)),
the process pool and tessellation (→
[`cad-generation`](../cad-generation/requirements.md)), the millimetre↔metre
conversion itself (→ `app/converters/`, owned by `wing-design` /
`fuselage-design`), and any HTTP surface at all.

## Business Rules

### Governance and units

- **BR-CT1 — The frozen/editable split is a project rule, not a code guard.** 🟢
  `cad_designer/CLAUDE.md` is the authority. **Read-only:**
  `airplane/aircraft_topology/**` and `airplane/GeneralJSONEncoderDecoder.py`
  — bugs and SonarQube findings inside them are *deliberately not fixed*.
  **Open for change:** `airplane/creator/**` (new Creators),
  `airplane/geometry/**` (actively developed feature code),
  `cq_plugins/`, `decorators/`.
  The single approved topology change is gh-934's `Turbulator` plus the
  `turbulator` parameter on `WingSegment` / `WingConfiguration`.
  Enforcement is by **exclusion, not code**: `sonar.exclusions = …,cad_designer/**`
  (`sonar-project.properties:10`) and
  `extend-exclude = [..., "cad_designer", "test", ...]`
  (`pyproject.toml:122-129`) — ≈22 000 LOC that is neither linted nor measured.
  ADR 0002.
- **BR-CT2 — Millimetres throughout, wing-local frame.** 🟢 Every dimension in
  `cad_designer/` is millimetres; the frame origin is the root leading edge with
  z up. `app/converters/` scales to metres for the database and AeroSandbox
  (ADR 0001). There is no type-level unit — the invariant is positional.

### The Creator contract

- **BR-CT3 — `create_shape` is a template method; `_create_shape` is the only
  subclass hook.** 🟢 `AbstractShapeCreator.create_shape(input_shapes=None,
  **kwargs)` (`AbstractShapeCreator.py:49-61`) resolves the upstream shapes,
  adjusts the log level, calls the abstract
  `_create_shape(shapes_of_interest, input_shapes, **kwargs)`, restores the log
  level and returns the result. A subclass never overrides `create_shape`.
- **BR-CT4 — Positional shape slots are filled most-significant-LAST.** 🟢
  `return_needed_shapes` (l.79-95) replaces every `None` entry in
  `shapes_of_interest_keys` with a key taken from
  `input_shapes.keys().__reversed__()`. If there are more `None` slots than
  input shapes it raises
  `KeyError(f'{self.identifier}: there are less input_shapes than shapes_needed.')`
  **before** any lookup. The ordering of `input_shapes` is therefore load-bearing
  and is guaranteed by [BR-CT9](#the-construction-tree).
- **BR-CT5 — A missing declared shape raises, naming the step.** 🟢
  `check_if_shapes_are_available` (l.63-77) raises
  `KeyError(f"shapes are missing in step '{self.identifier}': {missing}")`.
  A `None` list of needed shapes yields `{}` rather than raising.
- **BR-CT6 — A step mutates the ROOT logger level process-wide.** 🟢
  `create_shape` reads `logging.getLogger().getEffectiveLevel()`, lowers it to
  `self.loglevel` when `self.loglevel < effective`, and restores the *previously
  effective* level after `_create_shape` (l.53-60). 🟡 This is process-global and
  not thread-safe — two concurrent plan executions in the same process interleave
  log levels, and the restore writes an explicit level where none may have been
  set before.
- **BR-CT7 — The identifier is the output key, and a collision overwrites
  silently.** 🟢 Documented on `identifier` (l.20-27): `<identifier>` for a
  single shape, `<identifier>.<known_name>` for named outputs,
  `<identifier>[i]` for indexed ones. "If used several times the shape will be
  overwritten in future steps" — there is no uniqueness check anywhere.
- **BR-CT8 — The base-class `loglevel` default is `FATAL`, the authoring
  convention is `INFO`.** 🟢 `AbstractShapeCreator.__init__` defaults to
  `logging.FATAL` (50); `_creator_template.py:95` sets `loglevel: int =
  logging.INFO` (20) and the template states the divergence explicitly
  ("loglevel default is logging.INFO (not the base class's FATAL)").
- **BR-CT9 — A new Creator must be re-exported from its subpackage
  `__init__.py`.** 🟢 `_creator_template.py:18` states it as step 5 of the
  authoring recipe; the mechanism is [BR-CT13](#serialisation). A Creator that
  is not re-exported can be constructed in Python but can never be decoded from
  a stored plan.

### The construction tree

- **BR-CT10 — A `ConstructionStepNode` never declares its own shape
  requirements.** 🟢 Its constructor calls
  `super().__init__(f"{creator.identifier}", shapes_of_interest_keys=None)`
  (`ConstructionStepNode.py:24`), so the node's own `create_shape` skips
  `return_needed_shapes` entirely and delegates resolution to the wrapped
  Creator. The node's identifier **is** its creator's identifier.
  `ConstructionRootNode`'s identifier is `f"{creator_id}.root"`
  (`ConstructionRootNode.py:24`).
- **BR-CT11 — Traversal threads a growing registry and never mutates the
  caller's dict.** 🟢 `ConstructionStepNode._create_shape` (l.48-76):

  ```
  output_shapes = self.creator.create_shape(input_shapes=input_shapes, **kwargs)

  _input_shapes = {} if input_shapes is None else input_shapes.copy()
  for key in output_shapes:            # drop re-created keys first …
      _input_shapes.pop(key, None)
  _input_shapes.update(output_shapes)  # … so the newest keys land LAST

  kwargs.update(output_shapes)
  for succ in self.successors.values():
      kwargs.update(succ.create_shape(_input_shapes, **kwargs))
  return kwargs                        # every shape produced so far
  ```

  The pop-then-update dance exists *only* to guarantee the ordering BR-CT4
  depends on. The copy exists so a sibling branch cannot observe a child's
  mutations.
- **BR-CT12 — The root isolates top-level branches.** 🟢
  `ConstructionRootNode._create_shape` (l.48-58) hands **every** top-level
  successor `input_shapes={}`; only `kwargs` carries the accumulated registry.
  Consequence: positional (`None`) slot resolution works *within* a branch and
  **never across** top-level branches, while named references work everywhere.
- **BR-CT13 — `JSONStepNode` decodes eagerly at construction time.** 🟢
  (`JSONStepNode.py`) It opens `json_file_path`, decodes the sub-tree with
  `GeneralJSONDecoder(**kwargs)`, adopts the decoded node's `creator` and
  `successors`, and stores the injected kwargs privately as `_to_be_injected`.
  `successors` and `creator` are popped from `kwargs` before `super().__init__`.
  All runtime config must therefore be available when the node is *built*, not
  when it is *executed*.

### Serialisation

- **BR-CT14 — Only public attributes are serialised.** 🟢
  `GeneralJSONEncoder.default` (l.20-25) emits
  `{k: v for k, v in o.__dict__.items() if not k.startswith('_')}` plus
  `"$TYPE" = o.__class__.__name__`. This is *why* the authoring contract says
  runtime-injected config must be stored as `self._private`
  (`_creator_template.py:27-29`, l.91): a public field would be serialised into
  the stored plan and then re-injected at decode time.
- **BR-CT15 — `$TYPE` resolves against exactly one module namespace.** 🟢
  `GeneralJSONDecoder.object_hook` does
  `getattr(sys.modules[__name__], dic["$TYPE"])` (l.196-198) where `__name__` is
  `cad_designer.airplane.GeneralJSONEncoderDecoder`. The resolvable universe is
  therefore exactly what that module imports: `ConstructionRootNode`,
  `ConstructionStepNode`, and `from cad_designer.airplane.creator import *`
  (l.4-7). **Topology classes are not resolvable and never appear in a plan
  JSON.** An unknown name raises `AttributeError`.
- **BR-71 — Renaming or deleting a Creator invalidates every stored plan that
  references it.** 🟢 (global rule, `domain.md` §2.10) A direct corollary of
  BR-CT15. Evidenced today: 9 of the 32 `$TYPE` names used by
  `components/constructions/*.json` no longer exist, so
  `wings.root.json`, `fuselage.root.json` and `full_wing.json` are undecodable.
  See [BR-CT21](#known-defects-preserved-by-policy).
- **BR-CT16 — `**kwargs` in `__init__` switches the decode contract.** 🟢
  (l.201-210) If the target class's `__init__` accepts `**kwargs`, the **whole
  JSON dict plus all decoder kwargs** are passed. Otherwise the dict is
  intersected with the `__init__` parameter names and the matching decoder
  kwargs are overlaid on top. 🟡 In the `**kwargs` branch the decoder mutates
  the parsed `dic` in place (`intersection_dict = dic; intersection_dict.update(...)`).
- **BR-CT17 — JSON strings are coerced to the annotated scalar type,
  locale-aware.** 🟢 `_coerce_params` (l.125-176) reads
  `cls.__init__.__annotations__`, resolves the base type through `NewType`
  (`__supertype__`), `Annotated`, pydantic `confloat`, and **string annotations**
  produced by `from __future__ import annotations`
  (`_resolve_base_type`, l.28-84). Numeric strings pass through
  `_normalize_numeric_string` (l.95-122):

  ```
  "0,1"      → "0.1"       comma as decimal separator
  "1.234,56" → "1234.56"   German: last separator wins → dot is thousands
  "1,234.56" → "1234.56"   English: last separator wins → comma is thousands
  "1234"     → "1234"      unchanged
  ```

  A `None` value, or a key with no annotation, passes through untouched. A
  failed coercion logs `"Type coercion failed for %s.%s: …"` and **keeps the raw
  value** rather than raising.
- **BR-CT18 — A `list[...]` annotation receiving a bare string is wrapped, never
  iterated.** 🟢 (l.147-149) `["fuselage"]`, not `["f","u","s",…]`. An empty or
  whitespace-only string yields `[]`. This guard is checked **before**
  `_resolve_base_type`, which matters because `_resolve_base_type(list[str])`
  would otherwise return `str` via its `__args__[0]` unwrapping.
- **BR-CT19 — `creator_id` placeholders resolve from sibling parameters.** 🟢
  (l.212-223) `re.sub(r"\{(\w+)\}", …)` substitutes `{param}` from the same
  object's already-coerced values. A parameter that is missing, `None`, a `dict`
  or a `list` leaves the placeholder **verbatim** in the id.
- **BR-CT20 — Topology objects use a second, marker-less serialisation system.** 🟢
  Every topology class implements `__getstate__() -> dict` plus
  `@staticmethod from_json_dict(data) -> Self` with **no `$TYPE` marker**:
  `WingConfiguration`, `WingSegment`, `Airfoil`, `Spare`, `TrailingEdgeDevice`,
  `Turbulator`, `Servo`, `CoordinateSystem`, `AirplaneConfiguration`,
  `FuselageConfiguration`. This is the format behind the `/wingconfig` endpoints
  and `AirplaneConfiguration.to_dict()` / `save_to_json` / `save_to_zip`.
  **The two systems never mix**: a topology object reaches a running plan only as
  a **decoder kwarg** — `wing_config`, `fuselage_config`, `servo_information`,
  `printer_settings`, `engine_information`, `component_information`.

### Domain types and geometry classes

- **BR-CT21 — Literal types normalise case, and the direction differs.** 🟢
  (`airplane/types.py`) `CoordinateSystemBase`, `WingSegmentType` and `TipType`
  carry `BeforeValidator(lambda x: x.lower() …)`; `WingSides` carries
  `.upper()`. `Factor = confloat(ge=0, le=1.0)`;
  `DihedralInDegrees = confloat(ge=-180.0, le=180.0)`;
  `ShapeId` / `CreatorId` are `NewType(..., str)` and carry documentation, not
  validation.
- **BR-CT22 — `CoordinateSystem` validates before it decomposes, and the result
  is extrinsic.** 🟢 (`aircraft_topology/wing/CoordinateSystem.py`) It builds
  `R = np.matrix([xDir, yDir, zDir]).T`, requires `R·Rᵀ ≈ I` **and**
  `det R ≈ 1` (both `atol=1e-6`) or raises `InvalidRotationMatrixException`
  (l.94-95), then calls
  `Rotation.from_matrix(R).as_euler(order.lower(), degrees=True)` (l.98).
  🟡 The call site passes `'XYZ'` but the implementation lowercases it — in
  SciPy upper-case means **intrinsic** and lower-case **extrinsic**, so the
  stored `euler_xyz` is always the extrinsic decomposition regardless of the
  requested order. `InvalidRotationOrderException` (l.7) is declared and never
  raised. `from_json_dict` defaults each direction to the identity basis and the
  origin to `[0,0,0]`, and **recomputes** `euler_xyz` rather than reading the
  serialised value.
- **BR-CT23 — `ServoInformation` dimensions are read-only projections of its
  `Servo`.** 🟢 `length` / `width` / `height` are properties backed by
  `self.servo` whose setters are **no-ops that silently swallow writes**
  (`ServoInformation.py:30-35`). 🟡 The constructor's `height/width/length`
  arguments are used **only** to build a default `Servo` when `servo is None`; if
  a `servo` is supplied, those three arguments are silently ignored.
- **BR-CT24 — `AirplaneConfiguration` requires at least one wing and hard-codes
  the main wing.** 🟢 `__init__` sets `_main_wing_index = 0` and immediately
  evaluates `self._main_wing = self.wings[self._main_wing_index]`, so an empty
  `wings` list raises `IndexError` at construction. `asb_airplane` is a
  `cached_property` that converts with `mm_to_m_scale = 1.0e-3` and sets
  `analysis_specific_options = {asb.AVL: {"profile_drag_coefficient": 0.0}}`;
  🟡 it also assigns `self._asb_main_wing` as a side effect.
- **BR-CT25 — `Workplane.display` is environment-gated.** 🟢
  `@conditional_execute("DISPLAY_CONSTRUCTION_STEP")`
  (`decorators/general_decorators.py:5-21`) runs the decorated function only when
  the env var is set and its upper-case value is one of
  `"1" | "ON" | "TRUE" | "ENABLED"`; otherwise it logs a warning and **returns
  `self`**, keeping the fluent chain intact. This is the hook
  `construction-plans` toggles to stream shape events.
- **BR-CT26 — CadQuery extensions are installed by import, not by call.** 🟢
  `import cad_designer.cq_plugins` registers `Workplane.fix_shape`, `.offset3D`,
  `.display`, `.sewAndFix`, `.airfoil`, `.wing_root_segment`, `.wing_segment`
  and `Sketch.segmentToEdge`. `GeneralJSONEncoderDecoder.py:7` performs that
  import, so decoding a plan is what guarantees the plugins exist.
  `@fluent_init` (l.28-39) adds a static `.init()` factory and is applied to
  `WingConfiguration` only.

### Known defects preserved by policy

> These are 🟢 CONFIRMED behaviours of the frozen layer. ADR 0002 says they are
> **not to be fixed in place**. `tasks.md` separates the ones a
> re-implementation must reproduce from the ones it must not carry forward.

- **BR-CT27 — The perpendicular-spare branch is unreachable, by design decision.** 🟢
  `WingConfiguration._set_standard_spare_origin_vector` (l.354-372) defaults
  `spare_position_factor` to `0.25` when it is `None`, which makes the guard
  `spare.spare_vector is None and spare.spare_position_factor is not None`
  equivalent to `spare.spare_vector is None`, which makes the following
  `elif spare.spare_vector is None:` — the "make a perpendicular spare" branch —
  **dead**. `cad_designer/CLAUDE.md` names this branch explicitly and says it
  stays.
- **BR-CT28 — Nine deleted Creators are still referenced by three shipped plan
  JSONs.** 🟢 `FullWingLoftShapeCreator`, `FullFuselageLoftShapeCreator`,
  `WingRibCageCreator`, `ReinforcementPipesCreator`, `WingOffsetCreator`,
  `MirrorShapeCreator`, `EngineMountPanelShapeCreator`,
  `CPACSTrailingEdgeDeviceCreator`, `CPACSTrailingEdgeDeviceCutOutCreator`,
  `CPACSServoCutOutCreator` — 9 of 32 `$TYPE` names — break
  `wings.root.json`, `fuselage.root.json` and `full_wing.json`. The other five
  (`RV-7.root.json`, `RV-7-wing.root.json`, `eHawk-wing.root.json`,
  `punisher.root.json`, `configurator-test-wing.root.json`) resolve cleanly.
  **Latent, not live** — nothing under `app/` reads that directory; the files
  were authored by the third test root `test/` (23 files).
- **BR-CT29 — `ComponentInformation.get_z_axis` corrupts module-level
  singletons.** 🟢 **Carve-out granted, narrowly: fix the aliasing only** (`Q-CT-2`, maintainer-answered). The other two findings inside the frozen layer are documented, not fixed (ADR 0002). `z = gp_DZ` aliases the module global (l.4-6) and
  `gp_Dir.Rotate` mutates **in place**, so `gp_DX` / `gp_DY` / `gp_DZ` are
  permanently rotated after the first call. `get_middle_point` (l.27) builds
  `gp_Vec(trans_x + length/2, trans_y − width/2, trans_z − length/2)` — the z
  term uses `length/2` where `height/2` reads as intended. Rotation units are
  never stated while `gp_Ax1` rotation takes **radians** and `rot_*` are
  unlabelled floats.
- **BR-CT30 — `AirplaneConfiguration` carries a dormant copy of the gh-788
  reference-area bug.** 🟡 **Dead legacy path** — the second ASB entry point supersedes it (`Q-CT-3`, derived); it is the same "first wing is the main wing" error class that gh-788 fixed elsewhere. `_main_wing_index = 0` is the same "first wing is the
  main wing" assumption that made every coefficient ≈8× wrong for a tail-first
  import. gh-788 fixed the app converter to pick the largest-planform wing
  (`app/converters/model_schema_converters.py:761-817`); this copy was not
  touched. It is currently a **dead second ASB path** — the app builds an
  `AirplaneConfiguration` purely as an export payload
  (`aeroplane_service.py:288`) and uses `aeroplane_schema_to_asb_airplane` for
  all aerodynamics — so any future caller would silently inherit the bug.
- **BR-CT31 — Dead and unwired code that a re-implementation must not
  reproduce.** 🟢 **The hinge-type literal keeps all five values; `round_inside`/`round_outside` are declared-but-unimplemented, and the implementation follows** (`Q-CT-5`, maintainer-answered). Measured: no stored row uses either, so there is no harm to a beta user. The genuinely dead items (`AbstractConstructionStep.construct`, `create_XYZ_ted_sketch`, the unimported `scaleXyz` plugin) are recorded for removal under `P-DEAD-0`, but **stated in the spec rather than executed**, because they sit inside the ADR 0002 freeze.
  `AbstractConstructionStep.construct` (11 l.) has **no implementers**;
  `create_XYZ_ted_sketch` (`creator/wing/ted_sketch_creators.py:22`) is defined
  but absent from the `ted_sketch_creators` dispatch dict
  (`{"middle","top","top_simple"}`, keyed by `TrailingEdgeDevice.hinge_type`,
  consumed by `VaseModeWingCreator:662`);
  `cq_plugins/scaleXyz/__init__.py` registers `cq.Workplane.scaleXyz` but
  `cq_plugins/__init__.py` never imports it and nothing else does, so the plugin
  is **never installed** — and its implementation has a typo'd parameter
  `y_sacle` (`scaleXyz/scaleXyz.py:6`). The package also ships a stale
  `offest3D/.ipynb_checkpoints/` copy, and the plugin directory itself is
  misspelled `offest3D`.
- **BR-CT32 — `get_wing_workplane`'s error message names a value it never
  accepts.** 🟡 It branches on `parameters ∈ {"aerosandbox", "relative"}` but
  raises `ValueError(f"Unknown parameter type {self.parameters}, should be
  'absolute' or 'relative'")` (`WingConfiguration.py:394`).

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Provide `AbstractShapeCreator` with the `create_shape` template method and the abstract `_create_shape` hook | Must | A subclass implementing only `_create_shape` executes; overriding `create_shape` is never required |
| RF-02 | Resolve declared upstream shapes by name from the global registry | Must | A step declaring `["a","b"]` receives exactly those two shapes; a missing one raises `KeyError` naming the step |
| RF-03 | Resolve `None` slots positionally from `input_shapes`, most significant last | Must | With `input_shapes = {x:…, y:…}` and `shapes_of_interest_keys = [None]`, the step receives `y` |
| RF-04 | Raise before lookup when there are fewer inputs than `None` slots | Must | Two `None` slots with one input shape raises `KeyError` mentioning "less input_shapes than shapes_needed" |
| RF-05 | Lower and restore the root logger level around `_create_shape` | Should | The effective level inside `_create_shape` is `min(loglevel, previous)`; the previous level is restored afterwards |
| RF-06 | Name outputs `<identifier>`, `<identifier>.<name>`, `<identifier>[i]` | Must | A creator returning two named shapes produces exactly two dotted keys |
| RF-07 | Execute a construction tree depth-first, returning every shape produced so far | Must | The root's return value contains the outputs of every step in every branch |
| RF-08 | Order `input_shapes` so the newest keys are last, without mutating the caller's dict | Must | A sibling branch observes the pre-child `input_shapes`; the child sees its own output last |
| RF-09 | Isolate top-level branches from each other's `input_shapes` | Must | A top-level successor receives `{}` as `input_shapes` even when an earlier branch produced shapes |
| RF-10 | Load a sub-tree from a file with `JSONStepNode` and adopt its creator/successors | Should | The node behaves identically to the tree written inline in the parent plan |
| RF-11 | Encode a tree to JSON emitting only public attributes plus `$TYPE` | Must | A creator with `self._config` round-trips without the private field appearing in the JSON |
| RF-12 | Decode `$TYPE` by name against the encoder/decoder module namespace | Must | A registered Creator decodes; an unregistered or removed one raises `AttributeError` |
| RF-13 | Pass the whole dict + decoder kwargs when `__init__` accepts `**kwargs`, otherwise the intersection | Must | A creator with `**kwargs` receives `wing_config`; one without receives only its declared parameters |
| RF-14 | Coerce JSON strings to the annotated scalar type, locale-aware | Must | `"0,1"` → `0.1`; `"1.234,56"` → `1234.56`; an uncoercible value logs a warning and survives verbatim |
| RF-15 | Wrap a bare string into a one-element list when the annotation is `list[...]` | Must | `"fuselage"` becomes `["fuselage"]`, never a list of characters |
| RF-16 | Substitute `{param}` placeholders in `creator_id` from sibling values | Should | `"{wing_index}.loft"` with `wing_index = "main"` yields `"main.loft"`; an unknown `{foo}` survives verbatim |
| RF-17 | Provide `__getstate__` / `from_json_dict` on every topology class, with no type marker | Must | A `WingConfiguration` round-trips through the pair without any `$TYPE` key |
| RF-18 | Keep topology objects out of plan JSON, injecting them only as decoder kwargs | Must | No stored plan contains a `WingConfiguration`; the decoder receives it as `wing_config` |
| RF-19 | Normalise literal-type case (lower for most, upper for `WingSides`) | Should | `"Root"` validates as `"root"`; `"both"` validates as `"BOTH"` |
| RF-20 | Validate a rotation matrix before decomposing it to Euler angles | Must | A non-orthonormal basis raises `InvalidRotationMatrixException` rather than producing angles |
| RF-21 | Resolve a spar's origin and vector from `spare_position_factor`, defaulting to `0.25` | Must | A spar with no `spare_position_factor` and no `spare_vector` gets the quarter-chord standard vector |
| RF-22 | Convert an `AirplaneConfiguration` to an AeroSandbox airplane at `mm_to_m_scale = 1e-3` | Could | A 1000 mm chord becomes a 1.0 m ASB chord; `profile_drag_coefficient = 0.0` is set for AVL |
| RF-23 | Register the CadQuery extensions on import of `cad_designer.cq_plugins` | Must | After the import, `Workplane.sewAndFix` and `Sketch.segmentToEdge` exist |
| RF-24 | Gate `Workplane.display` on `DISPLAY_CONSTRUCTION_STEP` and return `self` when disabled | Must | With the var unset, `display()` logs a warning and the fluent chain continues unchanged |
| RF-25 | Provide 29 registered Creators across five categories | Must | Every class listed in a subpackage `__init__.py` is reachable through `from cad_designer.airplane.creator import *` |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Correctness | Shape-registry ordering is an explicit invariant, maintained by a pop-then-update on every step | `ConstructionStepNode.py:64-71` | 🟢 |
| Correctness | A rotation basis is validated before decomposition, so a malformed frame fails loudly | `CoordinateSystem.py:76-95` | 🟢 |
| Correctness | Type coercion never raises — it logs and preserves the raw value, so one bad field cannot abort a decode | `GeneralJSONEncoderDecoder.py:169-175` | 🟢 |
| Compatibility | Stored plans are versionless; class **names** are the compatibility contract | `GeneralJSONEncoderDecoder.py:196-198` | 🟢 |
| Compatibility | Locale-aware numeric parsing accepts German and English decimal formats from the frontend | `_normalize_numeric_string`, l.95-122 | 🟢 |
| Maintainability | ≈22 k LOC is deliberately excluded from lint and coverage; changes are governed by policy instead | `sonar-project.properties:10`, `pyproject.toml:122-129` | 🟢 |
| Portability | The whole module requires CadQuery/OCCT; consumers import it defensively and degrade | ADR 0017; `construction_plan_service` returns `[]` on `ImportError` | 🟢 |
| Observability | Per-step log verbosity is controllable through the plan itself (`loglevel` on every node) | `AbstractShapeCreator.py:53-60` | 🟢 |
| Observability | Visual debugging is opt-in through an env var, with zero cost when disabled | `decorators/general_decorators.py:5-21` | 🟢 |
| Concurrency | 🟡 Not thread-safe: the root logger level and the display gate are process-global | `AbstractShapeCreator.py:53-60`; `general_decorators.py:14` | 🟡 |

## Acceptance Criteria

```gherkin
Feature: Creator contract

  Scenario: A declared upstream shape is delivered to the subclass hook
    Given a creator whose shapes_of_interest_keys is ["wing.loft"]
    And a registry containing a shape under "wing.loft"
    When create_shape is called
    Then _create_shape receives shapes_of_interest containing exactly "wing.loft"

  Scenario: A missing declared shape is rejected by name
    Given a creator whose shapes_of_interest_keys is ["wing.loft"]
    And a registry that does not contain "wing.loft"
    When create_shape is called
    Then a KeyError is raised
    And the message contains the creator's identifier and "wing.loft"

  Scenario: A positional slot takes the most recent input shape
    Given input_shapes ordered as "first" then "second"
    And a creator whose shapes_of_interest_keys is [None]
    When create_shape is called
    Then the creator receives "second"

  Scenario: Too few input shapes for the positional slots is rejected early
    Given input_shapes containing one shape
    And a creator whose shapes_of_interest_keys is [None, None]
    When create_shape is called
    Then a KeyError is raised before any shape lookup happens
    And the message mentions that there are less input_shapes than shapes_needed

Feature: Construction-tree traversal

  Scenario: The newest shape is last in the child's input_shapes
    Given a step whose creator outputs "step.out"
    And input_shapes already containing "earlier"
    When the step executes and calls its successor
    Then the successor's input_shapes ends with "step.out"
    And the caller's original input_shapes dict is unchanged

  Scenario: A re-created key is moved to the end rather than duplicated
    Given input_shapes containing "shape"
    And a step whose creator also outputs "shape"
    When the step executes
    Then the successor's input_shapes contains "shape" exactly once
    And "shape" is the last key

  Scenario: Positional resolution does not cross top-level branches
    Given a root with two top-level successors
    And the first successor produces a shape
    When the second successor executes
    Then its input_shapes is empty
    And a positional slot in that branch raises a KeyError

Feature: Plan serialisation

  Scenario: A tree survives an encode-decode round trip
    Given a construction tree with a private _config attribute on one creator
    When it is encoded with GeneralJSONEncoder and decoded with GeneralJSONDecoder
    Then the JSON contains no key starting with an underscore
    And every node carries a $TYPE equal to its class name
    And the decoded tree produces the same shape keys as the original

  Scenario: A removed Creator makes a stored plan undecodable
    Given a stored plan referencing $TYPE "WingRibCageCreator"
    And no class of that name exists in the encoder/decoder namespace
    When the plan is decoded
    Then an AttributeError is raised

  Scenario: A German decimal string is coerced correctly
    Given a creator parameter annotated as float
    And the stored JSON value is the string "1.234,56"
    When the plan is decoded
    Then the parameter value is 1234.56

  Scenario: An uncoercible value does not abort the decode
    Given a creator parameter annotated as float
    And the stored JSON value is the string "not-a-number"
    When the plan is decoded
    Then a warning is logged naming the class and the parameter
    And the parameter keeps the raw string value

  Scenario: A bare string for a list parameter is wrapped
    Given a creator parameter annotated as list[ShapeId]
    And the stored JSON value is the string "fuselage"
    When the plan is decoded
    Then the parameter value is the list ["fuselage"]

  Scenario: An unresolvable placeholder survives verbatim
    Given a creator_id of "{wing_index}.loft" and no wing_index parameter
    When the plan is decoded
    Then the creator_id is still "{wing_index}.loft"

Feature: Topology objects

  Scenario: A wing configuration round-trips without a type marker
    Given a WingConfiguration in millimetres
    When __getstate__ is serialised and passed to from_json_dict
    Then the reconstructed object is equivalent
    And the serialised dict contains no $TYPE key

  Scenario: A malformed rotation basis is rejected
    Given direction vectors that are not orthonormal
    When a CoordinateSystem is constructed
    Then InvalidRotationMatrixException is raised
    And no Euler angles are produced

  Scenario: An aircraft with no wings cannot be constructed
    Given an empty list of wings
    When an AirplaneConfiguration is constructed
    Then an IndexError is raised while resolving the main wing

Feature: CadQuery extensions

  Scenario: The display hook is inert when the environment variable is unset
    Given DISPLAY_CONSTRUCTION_STEP is not set
    When a creator calls workplane.display(name="x")
    Then a warning is logged
    And the same workplane is returned so the fluent chain continues

  Scenario: The display hook fires when enabled
    Given DISPLAY_CONSTRUCTION_STEP is "ON"
    When a creator calls workplane.display(name="x")
    Then the decorated function executes
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| The Creator contract (RF-01…RF-06) | Must | Every one of the 29 Creators and both node types depend on it; it is the module's public API |
| Tree traversal and registry ordering (RF-07…RF-09) | Must | Positional slot resolution is only correct because of the ordering guarantee; getting it wrong silently builds the wrong solid |
| `$TYPE` encode/decode (RF-11…RF-13) | Must | The only persistence format for `construction_plans.tree_json`; a mismatch makes every stored plan unloadable |
| Type coercion and the `list[...]` guard (RF-14, RF-15) | Must | The frontend submits form values as strings; without the guard a shape key is iterated character-by-character |
| Topology `__getstate__` / `from_json_dict` (RF-17, RF-18) | Must | The `/wingconfig` endpoints and the whole `wing-design` round-trip ride on it |
| Rotation-matrix validation (RF-20) | Must | A silently wrong frame propagates through every downstream segment transform |
| Spar origin/vector resolution (RF-21) | Must | Consumed by `wing-design`'s solver; the `0.25` default is load-bearing |
| Placeholder substitution (RF-16) | Should | A convenience for authored plans; a literal id always works |
| `JSONStepNode` sub-tree loading (RF-10) | Should | Used by the authored `test/` plans; the app inlines trees instead |
| Literal case normalisation (RF-19) | Should | Tolerance for hand-authored JSON; canonical values always validate |
| Log-level manipulation (RF-05) | Should | Diagnostics only, but plans in the wild set it per node |
| `AirplaneConfiguration.asb_airplane` (RF-22) | Could | A second ASB path the app does not use; kept for the export payload and offline analysis |
| Fixing the perpendicular-spare dead branch | Won't | Deliberately frozen (ADR 0002, BR-CT27); named explicitly in `cad_designer/CLAUDE.md` |
| Fixing `gp_D*` singleton mutation in place | Won't (this module) | Frozen topology; a re-implementation must not reproduce it, but the current file stays untouched |
| Fixing `_main_wing_index = 0` in place | Won't (this module) | Dormant path; the live fix lives in `app/converters/` (gh-788) |
| Migrating the three undecodable plan JSONs | Won't (this module) | Authored by the `test/` root, unread by `app/`; ownership unresolved |
| `AbstractConstructionStep`, `scaleXyz`, `create_XYZ_ted_sketch` | Won't | Dead code with no implementers, no registration and no dispatch entry |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `cad_designer/airplane/AbstractShapeCreator.py` (95 l.) | `AbstractShapeCreator`, `create_shape`, `return_needed_shapes`, `check_if_shapes_are_available`, `identifier` | 🟢 |
| `cad_designer/airplane/ConstructionStepNode.py` (77 l.) | `ConstructionStepNode._create_shape`, `append`, `MutableMapping` protocol | 🟢 |
| `cad_designer/airplane/ConstructionRootNode.py` (59 l.) | `ConstructionRootNode._create_shape`, `f"{creator_id}.root"` | 🟢 |
| `cad_designer/airplane/JSONStepNode.py` (24 l.) | eager sub-tree decode, `_to_be_injected` | 🟢 |
| `cad_designer/airplane/AbstractConstructionStep.py` (11 l.) | `construct` — no implementers | 🟢 (dead) |
| `cad_designer/airplane/GeneralJSONEncoderDecoder.py` (224 l.) | `GeneralJSONEncoder.default`, `GeneralJSONDecoder.object_hook`, `_coerce_params`, `_resolve_base_type`, `_is_list_type`, `_normalize_numeric_string` | 🟢 |
| `cad_designer/airplane/types.py` (38 l.) | `Factor`, `DihedralInDegrees`, `CoordinateSystemBase`, `WingSegmentType`, `TipType`, `WingSides`, `ShapeId`, `CreatorId` | 🟢 |
| `cad_designer/airplane/creator/**` (31 modules, ≈3 600 l.) | 29 registered Creators + `ted_sketch_creators` dispatch + `_creator_template.py` | 🟢 |
| `cad_designer/airplane/aircraft_topology/wing/CoordinateSystem.py` | `CoordinateSystem`, `_is_valid_rotation_matrix`, `_rotation_matrix_to_euler_angles` | 🟢 read-only |
| `cad_designer/airplane/aircraft_topology/wing/WingConfiguration.py` (1 050 l.) | `_set_standard_spare_origin_vector`, `get_wing_workplane` | 🟢 read-only |
| `cad_designer/airplane/aircraft_topology/components/ComponentInformation.py` | `ComponentInformation`, `gp_DX/DY/DZ`, `get_middle_point`, `get_z_axis` | 🟢 read-only |
| `cad_designer/airplane/aircraft_topology/components/ServoInformation.py` | `ServoInformation` read-only dimension properties | 🟢 read-only |
| `cad_designer/airplane/aircraft_topology/components/EngineInformation.py` | `down_thrust → rot_y`, `side_thrust → rot_z` | 🟢 read-only |
| `cad_designer/airplane/aircraft_topology/airplane/AirplaneConfiguration.py` | `__init__`, `to_dict`, `save_to_json`, `save_to_zip`, `asb_airplane`, `airplane_analysis` | 🟢 read-only |
| `cad_designer/airplane/aircraft_topology/printer3d/Printer3dSettings.py` | `Printer3dSettings` defaults | 🟢 read-only |
| `cad_designer/cq_plugins/**` | `fix_shape`, `offest3D`, `display`, `sew_fix_shape`, `wing`, `segmentToEdge`, unregistered `scaleXyz` | 🟢 |
| `cad_designer/decorators/general_decorators.py` | `conditional_execute`, `fluent_init` | 🟢 |
| `cad_designer/airplane/geometry/**` | spar/section pipeline — **editable**, specified in [`wing-design`](../wing-design/requirements.md) | 🟢 cross-referenced |
| `cad_designer/aerosandbox/**` | `convert2aerosandbox`, `aerodynamic_calculations`, `classification`, `wing_roundtrip` (857 l.); `slicing.py` → `fuselage-design` | 🟢 |
