# cad-designer-topology — Technical Design

> Module-level design. Focuses on HOW the module is built, derived from the
> legacy code. Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Library API in full: see [`contracts.md`](contracts.md).
> Behavioural slices: [`creator-execution-model/`](creator-execution-model/),
> [`wingconfiguration-coordinate-system/`](wingconfiguration-coordinate-system/),
> [`json-polymorphic-roundtrip/`](json-polymorphic-roundtrip/).
>
> ⚠ **Frozen layer (ADR 0002.)** `aircraft_topology/**` and
> `GeneralJSONEncoderDecoder.py` are read-only; `creator/**`, `geometry/**`,
> `cq_plugins/` and `decorators/` are open.

## Interface

### The Creator contract — `cad_designer/airplane/AbstractShapeCreator.py` (95 l.) 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `AbstractShapeCreator.__init__` | `(creator_id: CreatorId, shapes_of_interest_keys: list[ShapeId] \| None, loglevel: int = logging.FATAL)` | — | stores `loglevel` and `creator_id` **publicly**, `_shapes_of_interest_keys` privately (l.15-18) |
| `identifier` | property | `CreatorId` | returns `creator_id`; also the output-dict key. Docstring warns it must stay public or it will not be serialised (l.20-27) |
| `shapes_of_interest_keys` | property | `list[ShapeId]` | the declared upstream keys; `None` disables resolution entirely |
| `_create_shape` | `(shapes_of_interest, input_shapes, **kwargs)` | `dict[ShapeId, Workplane]` | **abstract** — the only subclass hook (l.33-47) |
| `create_shape` | `(input_shapes: dict = None, **kwargs)` | `dict[ShapeId, Workplane]` | template method (l.49-61) |
| `return_needed_shapes` | `(shapes_needed, input_shapes, **kwargs)` | `dict` | fills `None` slots from `reversed(input_shapes)` (l.79-95) |
| `check_if_shapes_are_available` | `(needed_shapes, **kwargs)` | `dict` | raises `KeyError` naming the step and the missing keys (l.63-77) |

### The construction tree 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `ConstructionStepNode.__init__` | `(creator: AbstractShapeCreator, successors: OrderedDict = None, **kwargs)` | — | `super().__init__(f"{creator.identifier}", shapes_of_interest_keys=None)` (l.24) — the node itself never declares shapes |
| `ConstructionStepNode._create_shape` | `(shapes_of_interest, input_shapes, **kwargs)` | `dict` | the traversal core, l.48-76 |
| `ConstructionStepNode.append` | `(value)` | `None` | `self.update({value.creator.identifier: value})` |
| `ConstructionRootNode.__init__` | `(creator_id: CreatorId, successors: OrderedDict = None)` | — | identifier `f"{creator_id}.root"`; sets `self._output_shapes = None` (private ⇒ unserialised) |
| `ConstructionRootNode._create_shape` | same | `dict` | hands each successor `input_shapes={}` (l.56-57) |
| `JSONStepNode.__init__` | `(json_file_path: str, **kwargs)` | — | eager decode; adopts `creator.creator` / `creator.successors` |
| `AbstractConstructionStep.construct` | `(input_shapes: list[Workplane], **kwargs)` | `list[Workplane]` | 🔴 abstract with **no implementers** |

Both node classes are `AbstractShapeCreator` **and** `MutableMapping` over their
`successors` `OrderedDict`, so a tree can be walked, indexed and mutated like a
dict. 🟢

### Serialisation — `cad_designer/airplane/GeneralJSONEncoderDecoder.py` (224 l.) 🟢

| Symbol | Purpose |
|---|---|
| `GeneralJSONEncoder.JSON_CLASS_TYPE_ID` | the literal `"$TYPE"` (l.18) |
| `GeneralJSONEncoder.default` | public attributes only + `$TYPE = o.__class__.__name__` (l.20-25) |
| `GeneralJSONDecoder.__init__` | splits its `**kwargs` into the `JSONDecoder` parameters and the payload injected into every decoded object (l.180-191) |
| `GeneralJSONDecoder.object_hook` | class resolution, parameter selection, coercion, placeholder substitution (l.193-224) |
| `_resolve_base_type` | unwraps `NewType`, `Annotated`, `confloat`, and string annotations (l.28-84) |
| `_is_list_type` | `list[...]` detection for both real and string annotations (l.87-92) |
| `_normalize_numeric_string` | locale-aware decimal normalisation (l.95-122) |
| `_coerce_params` | applies the above to the selected `__init__` parameters (l.125-176) |

### Domain literal types — `cad_designer/airplane/types.py` (38 l.) 🟢

| Name | Definition | Normalisation |
|---|---|---|
| `Factor` | `confloat(ge=0, le=1.0)` | — |
| `DihedralInDegrees` | `confloat(ge=-180.0, le=180.0)` | — |
| `CoordinateSystemBase` | `Literal["world","wing","root_airfoil","tip_airfoil"]` | `BeforeValidator` → `.lower()` |
| `WingSegmentType` | `Literal["root","segment","tip"]` | `.lower()` |
| `TipType` | `Literal["flat","round"]` | `.lower()` |
| `WingSides` | `Literal["LEFT","RIGHT","BOTH"]` | **`.upper()`** |
| `ShapeId` / `CreatorId` | `NewType(..., str)` | documentation only, no validation |
| `TurbulatorForm` | `Literal["zigzag","dots","thread"]` (`wing/Turbulator.py:5`) | — |

### Component and configuration classes (frozen) 🟢

| Class | Constructor | File |
|---|---|---|
| `Position` | `(x, y, z)` + `get_x/y/z` | `aircraft_topology/Position.py:1` |
| `ComponentInformation` | `(height, width, length: PositiveFloat, rot_x/rot_y/rot_z: float = 0.0, trans_x/trans_y/trans_z: float = 0.0)` | `components/ComponentInformation.py:9` |
| `ServoInformation(ComponentInformation)` | `(height, width, length, lever_length: NonNegativeFloat, rot_*, trans_*, servo: Servo \| None = None)` | `components/ServoInformation.py:35` |
| `EngineInformation(ComponentInformation)` | `(down_thrust, side_thrust, position: Position, length, width, height, screw_hole_circle, mount_box_length, screw_din_diameter, screw_length, rot_x = 0.0)` | `components/EngineInformation.py:8` |
| `Printer3dSettings` | `(layer_height = 0.24, wall_thickness = 0.42, rel_gap_wall_thickness = 0.075)` mm | `printer3d/Printer3dSettings.py:4` |
| `CoordinateSystem` | `(xDir, yDir, zDir, origin)` → derives `euler_xyz` (degrees) | `wing/CoordinateSystem.py:29` |
| `AirplaneConfiguration` | `(name, total_mass_kg, wings: list[WingConfiguration], fuselages: list[FuselageConfiguration] \| None = None)` | `airplane/AirplaneConfiguration.py:21` |

The wing-side topology constructors (`WingConfiguration`, `WingSegment`,
`Airfoil`, `Spare`, `TrailingEdgeDevice`, `Turbulator`) are tabled under
[`wing-design`](../wing-design/design.md) and not repeated here. 🟢

### Creator inventory — 29 registered classes 🟢

| Package | Creators |
|---|---|
| `cad_operations/` (9) | `AddMultipleShapesCreator`, `Cut2ShapesCreator`, `CutMultipleShapesCreator`, `Fuse2ShapesCreator`, `FuseMultipleShapesCreator`, `Intersect2ShapesCreator`, `RepairFacesShapeCreator`, `ScaleRotateTranslateCreator`, `SimpleOffsetShapeCreator` |
| `wing/` (3) | `WingLoftCreator`, `VaseModeWingCreator` (1 173 l.), `StandWingSegmentOnPrinterCreator` |
| `fuselage/` (9) | `EngineCapeShapeCreator`, `EngineCoverAndMountPanelAndFuselageShapeCreator`, `EngineMountShapeCreator`, `FuselageElectronicsAccessCutOutShapeCreator`, `FuselageReinforcementShapeCreator`, `FuselageShellShapeCreator`, `FuselageWingSupportShapeCreator`, `WingAttachmentBoltCutoutShapeCreator`, `WingReinforcementShapeCreator` |
| `export_import/` (6) | `StepImportCreator`, `IgesImportCreator`, `ExportToIgesCreator`, `ExportToStepCreator`, `ExportTo3mfCreator`, `ExportToStlCreator` |
| `components/` (2) | `ComponentImporterCreator`, `ServoImporterCreator` |

`creator/__init__.py` is five star-imports of the subpackages; each subpackage
`__init__.py` is an explicit re-export list. `wing/ted_sketch_creators.py` is
**not** a Creator module — it is a dict dispatch
`{"middle", "top", "top_simple"}` keyed by `TrailingEdgeDevice.hinge_type` and
consumed by `VaseModeWingCreator:662`; it is intentionally absent from
`wing/__init__.py`. 🟢

## Main Flow

### F1 — Executing one Creator (`create_shape`) 🟢

```
create_shape(input_shapes, **kwargs):

  1. if shapes_of_interest_keys is not None:
         shapes_of_interest = return_needed_shapes(shapes_of_interest_keys,
                                                   input_shapes, **kwargs)
     else:
         shapes_of_interest = None                      # l.50-52

  2. actual = logging.getLogger().getEffectiveLevel()
     if self.loglevel < actual:
         logging.getLogger().setLevel(self.loglevel)    # l.54-56

  3. result = self._create_shape(shapes_of_interest, input_shapes, **kwargs)

  4. logging.getLogger().setLevel(actual)               # l.60  (unconditional)
  5. return result
```

Step 4 is **not** in a `finally`, so an exception inside `_create_shape` leaves
the lowered level in place for the rest of the process. 🟡 INFERRED consequence;
🟢 CONFIRMED by reading l.57-61.

`return_needed_shapes` (l.79-95):

```
len_input = 0 if input_shapes is None else len(input_shapes)
if count(None in shapes_needed) > len_input:
    raise KeyError(f'{identifier}: there are less input_shapes than shapes_needed.')

if input_shapes is not None:
    enum = input_shapes.keys().__reversed__()          # most significant LAST
    shapes_needed = [k if k is not None else next(enum) for k in shapes_needed]

shapes = check_if_shapes_are_available(shapes_needed, **kwargs)
return {key: shapes[key] for key in shapes_needed}     # preserves declared order
```

Note the resolved keys are looked up in **`kwargs`** — the global registry — not
in `input_shapes`. Positional resolution only *names* a shape; the value always
comes from the registry. 🟢

`check_if_shapes_are_available` (l.63-77):

```
shapes  = {k: kwargs[k] for k in needed_shapes if k in kwargs}
missing = [k for k in needed_shapes if k not in kwargs]      # via a set, order not stable
if missing:
    raise KeyError(f"shapes are missing in step '{identifier}': {missing}")
```

🟡 `missing` is built through a `set` comprehension, so the order of the names in
the error message is not deterministic.

### F2 — Walking the construction tree 🟢

```
ConstructionRootNode.create_shape()                       # shapes_of_interest_keys is None
└── _create_shape(None, input_shapes=None, **kwargs)
    for succ in successors.values():
        kwargs.update(succ.create_shape(input_shapes={}, **kwargs))   # ← EMPTY, per branch
    return kwargs

ConstructionStepNode._create_shape(_, input_shapes, **kwargs)
    output_shapes = self.creator.create_shape(input_shapes=input_shapes, **kwargs)

    _input_shapes = {} if input_shapes is None else input_shapes.copy()
    for key in output_shapes:
        _input_shapes.pop(key, None)          # remove, so update() re-appends at the END
    _input_shapes.update(output_shapes)

    kwargs.update(output_shapes)
    for succ in successors.values():
        kwargs.update(succ.create_shape(_input_shapes, **kwargs))
    return kwargs                              # every shape produced so far
```

Two invariants fall out of this:

- **Ordering** — `_input_shapes` always ends with the most recently produced
  shape, which is exactly what `return_needed_shapes` consumes first. Delete the
  pop loop and a re-created key would keep its old position, silently changing
  which shape a positional slot resolves to.
- **Isolation** — `input_shapes.copy()` means a successor cannot mutate what its
  siblings see; `kwargs`, by contrast, is deliberately shared and accumulating.

### F3 — Encoding a plan 🟢

```
json.dumps(root_node, cls=GeneralJSONEncoder)

GeneralJSONEncoder.default(o):
    dic = {k: v for k, v in o.__dict__.items() if not k.startswith('_')}
    dic["$TYPE"] = o.__class__.__name__
    return dic
```

Consequences, all deliberate:

- `_shapes_of_interest_keys` is private, so the **declared** keys are not stored;
  what is stored is the public parameter (e.g. `self.input_shape`) that the
  constructor re-assembles into `shapes_of_interest_keys`.
- `_config`-style runtime injections vanish, which is what makes a plan portable
  between aircraft.
- `ConstructionRootNode._output_shapes` never appears in the JSON.
- `JSONStepNode` stores `json_file_path` (public) but not `_to_be_injected`.

### F4 — Decoding a plan 🟢

```
json.loads(text, cls=GeneralJSONDecoder,
           wing_config=…, printer_settings=…, servo_information=…,
           engine_information=…, component_information=…)

__init__:  split kwargs → the JSONDecoder's own params vs. the injection payload
object_hook(dic):
    if "$TYPE" not in dic: return dic                       # plain dict passthrough
    cls = getattr(sys.modules["…GeneralJSONEncoderDecoder"], dic["$TYPE"])
    init_params = inspect.signature(cls.__init__).parameters

    if "kwargs" in init_params:
        intersection_dict = dic
        intersection_dict.update(self.kwargs)               # ALL injections
    else:
        intersection = {k: self.kwargs[k] for k in self.kwargs.keys() & init_params.keys()}
        intersection_dict = {k: dic[k]     for k in dic.keys()         & init_params.keys()}
        intersection_dict.update(intersection)              # injections WIN over stored values

    intersection_dict = _coerce_params(cls, intersection_dict)

    if isinstance(intersection_dict.get("creator_id"), str):
        creator_id = re.sub(r"\{(\w+)\}", replace_from_siblings, creator_id)

    return cls(**intersection_dict)
```

Because `object_hook` fires **bottom-up**, a `ConstructionStepNode`'s `creator`
and `successors` are already live objects by the time the node itself is
constructed. 🟢

Three behaviours worth pinning:

- Injected kwargs **override** stored values of the same name in both branches.
- In the `**kwargs` branch the parsed `dic` is mutated in place. 🟡 Harmless
  today (the dict is discarded) but it means the hook is not pure.
- Set-intersection (`dic.keys() & init_params.keys()`) drops any stored key the
  constructor does not declare — that is how a plan survives a Creator gaining
  or losing an optional parameter.

### F5 — Type coercion 🟢

```
_coerce_params(cls, params):
  raw_hints = cls.__init__.__annotations__ minus "return"     # AttributeError → params
  for key, value in params.items():
      if value is None or key not in raw_hints:  keep as-is

      if _is_list_type(hint) and isinstance(value, str):
          → [value] if value.strip() else []                  # the character-iteration guard
      if _is_list_type(hint) and not isinstance(value, list):
          → keep as-is

      target = _resolve_base_type(hint)                       # None → keep as-is
      float → float(_normalize_numeric_string(value))
      int   → int(float(_normalize_numeric_string(value)))
      bool  → bool(value)
      str   → str(value)
      on ValueError/TypeError → logging.warning(...) and keep the raw value
```

`_resolve_base_type` (l.28-84) handles, in order: **string** annotations
(`"float"`, `"confloat…"`, `"nonnegativeint"`, `"conint…"`, `"bool"`, `"str"`,
`"creatorid"`/`"shapeid"` → `str`, any hint containing `"factor"` → `float`, and
`Annotated[...]` by parsing the first argument out of the string); then
`NewType.__supertype__`; then `__origin__`/`__args__[0]` recursion; then the
four plain scalars. 🟡 The string branch is heuristic and case-insensitive, so a
parameter named with an unrelated type whose annotation string happens to
contain `"factor"` would be coerced to `float`.

The `__origin__` recursion is why the `list[...]` guard **must** run first:
`_resolve_base_type(list[str])` would otherwise return `str` and stringify the
list. 🟢

### F6 — The second serialisation system (topology objects) 🟢

```
obj.__getstate__()  -> plain dict, no marker
Class.from_json_dict(data) -> Class          @staticmethod
```

Implemented by `WingConfiguration`, `WingSegment`, `Airfoil`, `Spare`,
`TrailingEdgeDevice`, `Turbulator`, `Servo`, `CoordinateSystem`,
`AirplaneConfiguration`, `FuselageConfiguration`.

`AirplaneConfiguration` layers three envelopes on top:

```
to_dict()      → {"name", "total_mass_kg", "wings": [wing.__getstate__(), …],
                  "fuselages": [...]}          # "fuselages" omitted when falsy
save_to_json() → json.dump(to_dict(), indent=4)
save_to_zip()  → a temp tree with wings/ and fuselages/ subdirectories,
                 one JSON per object, zipped
```

`CoordinateSystem.__getstate__` emits `euler_xyz` as well, but
`from_json_dict` **ignores it** and recomputes from the direction vectors — so a
hand-edited `euler_xyz` is silently discarded. 🟢

### F7 — CadQuery extension installation 🟢

`cad_designer/cq_plugins/__init__.py` imports, in order:
`fix_shape.fix_shape`, `segmentToEdge`, `display`, `fix_shape`, `offest3D`
(*sic* — the directory name is misspelled), `sew_fix_shape`, `wing`.
Each submodule monkey-patches its function onto `cq.Workplane` (or `cq.Sketch`)
at import time.

`GeneralJSONEncoderDecoder.py:7` does `import cad_designer.cq_plugins`, which is
why decoding a plan is sufficient to guarantee the extensions exist — no
consumer has to remember the import. 🟢

`Workplane.display` is wrapped by `@conditional_execute("DISPLAY_CONSTRUCTION_STEP")`:

```
env = os.getenv("DISPLAY_CONSTRUCTION_STEP")
if env is not None and env.upper() in ["1", "ON", "TRUE", "ENABLED"]:
    return func(self, *args, **kwargs)
logging.warning(f"function '{func.__name__}' has been called, but has not been "
                f"executed as 'DISPLAY_CONSTRUCTION_STEP' is not set.")
return self                       # fluent chain preserved
```

🟡 The warning fires on **every** `display()` call in the disabled case, which is
once per creator per execution — noisy by design.

## Alternative Flows

- **No declared shapes (`shapes_of_interest_keys is None`):** resolution is
  skipped entirely and `_create_shape` receives `shapes_of_interest = None`.
  Both node classes take this path, always. 🟢
- **Empty declared list (`[]`):** `return_needed_shapes` runs, finds no `None`
  slots, and returns `{}` — the documented shape for self-contained,
  config-driven Creators. 🟢
- **`input_shapes is None`** (the first step of a branch): `return_needed_shapes`
  treats the length as `0`, so any `None` slot raises; `ConstructionStepNode`
  substitutes `{}` before copying. 🟢
- **Unknown `$TYPE`:** `getattr` raises `AttributeError` — not a domain error, so
  `construction-plans` wraps it into
  `ValidationError("Failed to decode construction plan: …")`. 🟢
- **Uncoercible parameter value:** logged as a warning, raw value preserved, and
  the object is constructed anyway — the failure surfaces later as a `TypeError`
  inside the Creator, or not at all. 🟡
- **Unresolvable `{placeholder}`:** left verbatim in `creator_id`, producing a
  step whose identifier literally contains braces and therefore a shape key that
  no other step can reference by hand. 🟢
- **Malformed rotation basis:** `InvalidRotationMatrixException` from
  `_is_valid_rotation_matrix`, raised **during construction** of the
  `CoordinateSystem`, before any geometry is built. 🟢
- **`AirplaneConfiguration` with no wings:** `IndexError` at construction time
  from `self.wings[0]`, not a domain error. 🟢
- **CadQuery absent (`linux/aarch64`):** importing anything in this module
  raises `ImportError`; consumers guard (`construction_plan_service.list_creators`
  returns `[]`, the CAD router is not mounted). ADR 0017. 🟢

## Dependencies

- **CadQuery / OCCT** — hard dependency of the entire module; `Workplane` is in
  the type signature of the Creator contract itself.
- **pydantic** — `confloat`, `PositiveFloat`, `NonNegativeFloat`,
  `BeforeValidator` in `types.py` and the component classes.
- **NumPy + SciPy** — `CoordinateSystem` rotation-matrix validation and Euler
  decomposition (`scipy.spatial.transform.Rotation`).
- **AeroSandbox** — imported at module scope by `AirplaneConfiguration` and the
  `cad_designer/aerosandbox/` bridge, so it is a hard import dependency of that
  file even though the app uses a different ASB path.
- **`cad_designer/airplane/geometry/**`** — editable feature code that consumes
  the topology classes; its algorithms belong to
  [`wing-design`](../wing-design/design.md).
- **Consumers (in-process, all one-way):** `cad-generation` (rebuilds a
  `WingConfiguration` in a worker and drives `WingLoftCreator`),
  `construction-plans` (decodes trees, reflects the Creator catalogue, executes),
  `wing-design` / `fuselage-design` (`app/converters/` mm↔m boundary),
  `openvsp-import` (STEP handling). None of them are imported *by* this module —
  the dependency direction is strictly inward. 🟢

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| The topology layer is frozen; only new Creators and `geometry/` may change | ADR 0002; `cad_designer/CLAUDE.md`; `sonar-project.properties:10` | 🟢 |
| Millimetres and a wing-local frame inside CAD; metres outside | ADR 0001; `cad_designer/CLAUDE.md` §Conventions | 🟢 |
| A template method with a single abstract hook, rather than an interface Creators implement freely | `AbstractShapeCreator.py:49-61`; the unused `AbstractConstructionStep` shows the abandoned alternative | 🟢 |
| Shape identity is a **string key in a flat registry**, not an object graph | `identifier` docstring l.20-27; `kwargs` threading in both node classes | 🟢 |
| Positional (`None`) slots resolve from an *ordered* dict rather than by index | `return_needed_shapes` l.90-92 + the pop/update dance in `ConstructionStepNode` l.64-71 | 🟢 |
| Top-level branches are isolated from each other's `input_shapes` | `ConstructionRootNode.py:56-57` | 🟢 |
| Serialisation is by class **name**, with no version field and no registry | `GeneralJSONEncoderDecoder.py:18-25, 196-198` | 🟢 |
| Privacy (`_` prefix) is the mechanism for excluding runtime config from storage | encoder l.22; `_creator_template.py:27-29` | 🟢 |
| Decoding is tolerant: coercion failures warn and preserve, unknown stored keys are dropped | `_coerce_params` l.169-175; set-intersection l.206-208 | 🟢 |
| Locale-aware numeric parsing, because the frontend submits form strings | `_normalize_numeric_string` l.95-122 | 🟢 |
| Topology objects use a **separate**, marker-less format and never enter a plan JSON | `__getstate__`/`from_json_dict` across the topology classes; decoder-kwarg injection | 🟢 |
| Visual debugging is an env-gated no-op rather than a parameter | `conditional_execute`, `general_decorators.py:5-21` | 🟢 |
| CadQuery extensions install on import, and the decoder forces that import | `cq_plugins/__init__.py`; `GeneralJSONEncoderDecoder.py:7` | 🟢 |
| The dead perpendicular-spare branch stays | ADR 0002; `cad_designer/CLAUDE.md`; `WingConfiguration.py:354-372` | 🟢 |

## Internal State

The module is **not** a service and holds no request-scoped state. What state
exists is either per-object or process-global:

- **Per execution, threaded explicitly** — the `kwargs` shape registry. It grows
  monotonically for the life of one `create_shape()` call on the root and is
  discarded afterwards. Keys are `ShapeId` strings; values are CadQuery
  `Workplane`s (and, for export Creators, whatever they pass through).
- **Per node** — `successors` (`OrderedDict`), `creator`, `creator_id`,
  `loglevel`; `ConstructionRootNode._output_shapes` is initialised to `None` and
  never written. 🟡 Vestigial.
- **Per topology object** — `WingConfiguration` caches segment workplanes
  ("cached for performance", `get_wing_workplane` docstring);
  `AirplaneConfiguration.asb_airplane` is a `cached_property` that also assigns
  `self._asb_main_wing` as a side effect.
- **Process-global, mutated at runtime** 🟡 — the root logger level
  (`AbstractShapeCreator.create_shape`), the `gp_DX/gp_DY/gp_DZ` singletons
  (`ComponentInformation.get_z_axis`), the monkey-patched CadQuery classes
  (installed once per process by import), and the
  `DISPLAY_CONSTRUCTION_STEP` env var that `construction-plans` toggles.

## Observability

- **Per-step log level.** Every node and Creator carries `loglevel`, serialised
  into the plan, and applied to the **root** logger for the duration of the step
  (`AbstractShapeCreator.py:53-60`). The authored blueprints use `50` on the
  structural nodes, `10` on the wing creator and `20` on the exporter. 🟢
- **Creator-authored progress logs.** The template prescribes
  `logging.info(f"processing '{keys}' --> '{self.identifier}'")` as the first
  statement of `_create_shape` (`_creator_template.py:135-139`). 🟢
- **Visual shape dumps.** `result.display(name=self.identifier,
  severity=logging.DEBUG)` — inert unless `DISPLAY_CONSTRUCTION_STEP` is set;
  when set, it is the event source `construction-plans` streams over SSE. 🟢
- **Coercion warnings.** `"Type coercion failed for %s.%s: value=%r, expected=%s (%s)"`
  is the only structured diagnostic the serialisation layer emits. 🟢
- **Disabled-display warnings.** One `logging.warning` per suppressed
  `display()` call. 🟡 High-volume by construction.
- **No metrics, traces or events.** Failures surface as exceptions to the caller;
  timing and success accounting belong to `construction-plans` and
  `cad-generation`. 🟢

## Risks and Gaps

- 🟡 **Nine deleted Creator classes** are still referenced by
  `components/constructions/{wings.root.json, fuselage.root.json, full_wing.json}`
  (9 of 32 `$TYPE` names). Latent — nothing under `app/` reads that directory —
  but the files are shipped in the repository and will fail on any attempt to
  load them.
- 🔴 **`ComponentInformation.get_z_axis` corrupts `gp_DX/gp_DY/gp_DZ`** for the
  whole process on first call, because `gp_Dir.Rotate` mutates in place and `z`
  is an alias, not a copy. Every later consumer of those singletons — including
  `get_middle_point` on any instance — sees rotated axes.
- 🔴 **`get_middle_point` uses `self.length/2` on the z term** where `height/2`
  reads as intended (`ComponentInformation.py:27`), and the sign pattern
  (`+x`, `−y`, `−z`) is undocumented.
- 🟢 **`euler_xyz` is display/serialisation only** — no consumer depends on the intrinsic/extrinsic distinction (`Q-CT-4`, resolved by code lookup). Previously the rotation units were unspecified: `rot_x/rot_y/rot_z` are bare floats fed
  to `gp_Ax1` rotations, which OCCT defines in **radians**; nothing in the class,
  its callers or the docstrings states which is intended.
- 🔴 **`AirplaneConfiguration._main_wing_index = 0`** is a dormant duplicate of
  the gh-788 reference-area bug on an ASB path the app does not currently call.
- 🔴 **`get_wing_workplane`'s error message names `'absolute'`**, a value the
  code never accepts — suggesting a rename to `"aerosandbox"` left the message
  behind.
- 🟢 **The hinge-type literal keeps all five values; `round_inside`/`round_outside` are declared-but-unimplemented, and the implementation follows** (`Q-CT-5`, maintainer-answered). Measured: no stored row uses either, so there is no harm to a beta user. The genuinely dead items (`AbstractConstructionStep.construct`, `create_XYZ_ted_sketch`, the unimported `scaleXyz` plugin) are recorded for removal under `P-DEAD-0`, but **stated in the spec rather than executed**, because they sit inside the ADR 0002 freeze. Previously dead code with no owner: `AbstractConstructionStep` (no implementers),
  `create_XYZ_ted_sketch` (not in the dispatch dict), `cq_plugins/scaleXyz`
  (never imported, and typo'd `y_sacle`), the stale
  `offest3D/.ipynb_checkpoints/` copy, and the misspelled `offest3D` package
  name itself.
- 🟡 **The log-level restore is not exception-safe.** `create_shape` restores the
  previous level on the normal path only (l.57-61), so a raising step leaves the
  root logger permanently lowered.
- 🟡 **Concurrency is unsupported but unguarded.** The root logger level, the
  display gate and the `gp_D*` singletons are all process-global. This is the
  same tension ADR 0005 records between `cad-generation`'s process pool and
  `construction-plans`' in-process execution.
- 🟡 **`_resolve_base_type`'s string branch is heuristic** — `"factor" in
  hint_lower → float` will coerce any parameter whose annotation string happens
  to contain "factor".
- 🟡 **`euler_xyz` is serialised but never deserialised**; a hand-edited value is
  silently recomputed from the direction vectors.
- 🟡 **The `**kwargs` decode branch mutates the parsed dict in place**, making
  `object_hook` impure.
- 🟢 **`InvalidRotationOrderException` is declared and never raised** — a
  placeholder for validation that was never written. Documented, not fixed.
