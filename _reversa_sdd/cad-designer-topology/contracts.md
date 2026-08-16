# cad-designer-topology — Internal Library Contract

> **This module exposes no HTTP surface.** Its contract is a **Python API
> consumed in-process** by [`cad-generation`](../cad-generation/contracts.md),
> [`construction-plans`](../construction-plans/contracts.md),
> [`wing-design`](../wing-design/contracts.md), `fuselage-design` and
> `openvsp-import` — plus **two on-disk serialisation formats** that outlive any
> single process: the `$TYPE` plan-tree dialect and the marker-less topology
> dialect.
>
> There is no versioning, no negotiation and no deprecation path. The
> compatibility contract is: **Python class names, constructor signatures, and
> the two JSON shapes below.** Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
>
> ⚠ Frozen layer (ADR 0002) — this document describes a contract to honour, not
> one to renegotiate.

## Contract surfaces at a glance 🟢

| # | Surface | Kind | Breaking change is… |
|---|---|---|---|
| 1 | `AbstractShapeCreator` | Python base class | any change to `create_shape` / `_create_shape` signatures or the resolution protocol |
| 2 | The construction tree | Python classes | any change to traversal order or `input_shapes` semantics |
| 3 | `$TYPE` plan JSON | on-disk / DB (`construction_plans.tree_json`) | renaming or deleting **any** Creator class |
| 4 | Topology JSON (`__getstate__` / `from_json_dict`) | on-disk / wire (`/wingconfig`) | renaming or retyping any public topology attribute |
| 5 | Decoder kwarg injection | Python calling convention | renaming `wing_config`, `printer_settings`, `servo_information`, `engine_information`, `component_information` |
| 6 | CadQuery monkey-patches | global namespace mutation | removing a `Workplane` / `Sketch` method any Creator calls |
| 7 | `DISPLAY_CONSTRUCTION_STEP` | environment variable | changing the accepted value set |

## Unit contract 🟢

| Quantity | Unit inside this module | Converted where |
|---|---|---|
| every length (chord, span, spar dimensions, servo box, printer settings) | **millimetres** | `app/converters/` (`scale = 0.001` mm→m, `1000.0` m→mm) |
| angles (`dihedral`, `incidence`, `twist`, `euler_xyz`) | **degrees** | not converted |
| `ComponentInformation.rot_x/rot_y/rot_z` | 🔴 **unspecified** — passed to `gp_Ax1`, which OCCT defines in radians | — |
| `AirplaneConfiguration.total_mass_kg` | kilograms | — |
| `AirplaneConfiguration.asb_airplane` output | metres (`mm_to_m_scale = 1.0e-3`) | internal to the property |
| frame | wing-local: origin at the root leading edge, **z up** | — |

There is no type-level unit anywhere; the invariant is positional and enforced
only by the converter layer. ADR 0001. 🟢

## 1 — `AbstractShapeCreator` 🟢

`cad_designer/airplane/AbstractShapeCreator.py` (95 l.)

```python
class AbstractShapeCreator(metaclass=abc.ABCMeta):
    def __init__(self,
                 creator_id: CreatorId,
                 shapes_of_interest_keys: list[ShapeId] | None,
                 loglevel: int = logging.FATAL) -> None: ...

    @property
    def identifier(self) -> CreatorId: ...              # == creator_id

    @property
    def shapes_of_interest_keys(self) -> list[ShapeId]: ...

    @abc.abstractmethod
    def _create_shape(self,
                      shapes_of_interest: dict[ShapeId, Workplane] | None,
                      input_shapes: dict[ShapeId, Workplane],
                      **kwargs) -> dict[ShapeId, Workplane]: ...

    def create_shape(self,
                     input_shapes: dict[ShapeId, Workplane] = None,
                     **kwargs) -> dict[ShapeId, Workplane]: ...

    def check_if_shapes_are_available(self, needed_shapes, **kwargs) -> dict: ...
    def return_needed_shapes(self, shapes_needed, input_shapes, **kwargs) -> dict: ...
```

### Implementer obligations 🟢

| # | Obligation | Consequence of breaking it |
|---|---|---|
| 1 | Implement **only** `_create_shape`; never override `create_shape` | log-level handling and shape resolution are skipped |
| 2 | Store domain parameters as **public** attributes **before** `super().__init__` | a private field is not serialised, so the plan loses the parameter |
| 3 | Store runtime-injected config as `self._private` | a public field is serialised into the stored plan and then shadowed by the injection |
| 4 | Return a dict keyed per the output convention (below) | downstream steps cannot reference the shape |
| 5 | Declare `shapes_of_interest_keys` as `[named]`, `[None]` (positional), `[]` (self-contained) or `None` (no resolution) | wrong upstream shape, or a `KeyError` |
| 6 | Be re-exported from the subpackage `__init__.py` | the class exists but can never be decoded from a stored plan |
| 7 | Default `loglevel` to `logging.INFO` in new Creators | the base default is `FATAL`, which silences the creator's own logs |

### `shapes_of_interest_keys` semantics 🟢

| Value | Behaviour |
|---|---|
| `None` | resolution skipped entirely; `_create_shape` receives `shapes_of_interest = None` |
| `[]` | `return_needed_shapes` runs and returns `{}` — the documented shape for config-driven Creators |
| `["a", "b"]` | both looked up in the **global registry** (`kwargs`); any missing key raises |
| `[None]` | filled from `input_shapes.keys()` **reversed** (most significant last), then looked up in the registry |
| `["a", None]` | mixed; the named key resolves from the registry, the slot from the inputs |

### Guaranteed exceptions 🟢

| Condition | Exception | Message |
|---|---|---|
| more `None` slots than input shapes | `KeyError` | `"{identifier}: there are less input_shapes than shapes_needed."` |
| a declared key absent from the registry | `KeyError` | `"shapes are missing in step '{identifier}': {missing}"` — 🟡 `missing` is built via a `set`, so its order is not stable |

Both are raised **before** `_create_shape` runs. 🟢

### Output-key convention 🟢

| Shape kind | Key |
|---|---|
| single output | `<identifier>` |
| named outputs | `<identifier>.<known_name>` — e.g. `engine_mount.cape` |
| indexed outputs | `<identifier>[i]` |
| pass-through (exporters) | return `shapes_of_interest` unchanged |

⚠ A repeated identifier **silently overwrites** the earlier shape. There is no
uniqueness check anywhere in the module. 🟢

### Side effect on the global logger 🟢

`create_shape` lowers the **root** logger to `self.loglevel` when it is below
the effective level and restores the previous level afterwards. 🟡 The restore
is not in a `finally`, so a raising step leaves the level lowered for the rest
of the process; and it is process-global, so concurrent executions interleave.

## 2 — The construction tree 🟢

```python
class ConstructionStepNode(AbstractShapeCreator, MutableMapping):
    def __init__(self,
                 creator: AbstractShapeCreator,
                 successors: OrderedDict[CreatorId, ConstructionStepNode] = None,
                 **kwargs) -> None: ...
    def append(self, value) -> None: ...        # keyed by value.creator.identifier

class ConstructionRootNode(AbstractShapeCreator, MutableMapping):
    def __init__(self,
                 creator_id: CreatorId,
                 successors: OrderedDict[CreatorId, ConstructionStepNode] = None) -> None: ...
    #  identifier == f"{creator_id}.root"

class JSONStepNode(ConstructionStepNode):
    def __init__(self, json_file_path: str, **kwargs) -> None: ...

class AbstractConstructionStep(metaclass=abc.ABCMeta):     # 🔴 no implementers
    @abc.abstractmethod
    def construct(self, input_shapes: list[Workplane], **kwargs) -> list[Workplane]: ...
```

Both node classes are also `MutableMapping` over `successors`, so a tree can be
indexed, iterated, measured and mutated like a dict. 🟢

### Execution contract 🟢

| Guarantee | Detail |
|---|---|
| **Entry point** | `root.create_shape()` — no arguments; the root declares `shapes_of_interest_keys=None` |
| **Return value** | the accumulated `kwargs` registry: **every** shape produced by **every** step, keyed by `ShapeId` |
| **Traversal** | depth-first, in `successors` insertion order |
| **Registry** | `kwargs` is shared and grows monotonically for the whole run |
| **`input_shapes` ordering** | always ends with the most recently produced shape (pop-then-update) — this is what makes positional resolution deterministic |
| **Non-mutation** | a step copies `input_shapes` before handing it to successors, so siblings cannot observe each other's mutations |
| **Branch isolation** | the root hands **every** top-level successor `input_shapes={}`; positional slots therefore never resolve across top-level branches, while named references always work |
| **`None` inputs** | `ConstructionStepNode` substitutes `{}`; `return_needed_shapes` treats the length as `0` |
| **A `ConstructionStepNode` never declares its own shape needs** | it always passes `shapes_of_interest_keys=None` to `super().__init__` and delegates to its creator |

### `JSONStepNode` timing contract 🟢

The sub-tree is decoded **in the constructor**, not at execution time. All
runtime config (`wing_config`, `printer_settings`, …) must therefore be
available when the node is **built**. `json_file_path` is public (and so
serialised); the injection payload is stored as `_to_be_injected` and is not.
`successors` and `creator` are popped from `kwargs` before delegating to
`ConstructionStepNode.__init__`.

## 3 — The `$TYPE` plan-tree format 🟢

Consumers: `construction_plans.tree_json` (DB), `components/constructions/*.json`
(files), and `cad_service.build_wing_blueprint` (synthesised in memory).

### Envelope 🟢

| Key | Type | Notes |
|---|---|---|
| `$TYPE` | `str` | `GeneralJSONEncoder.JSON_CLASS_TYPE_ID`; the class `__name__`, resolved with `getattr` on the `GeneralJSONEncoderDecoder` module namespace |
| `creator_id` | `str` | may contain `{param}` placeholders substituted from sibling values at decode time |
| `loglevel` | `int` | Python logging level; base-class default `FATAL` (50), template recommendation `INFO` (20) |
| `successors` | `dict[CreatorId, node]` | ordered; the frontend also emits a **list** form, which `construction-plans`' `_count_steps` and `_rewrite_export_paths` tolerate |
| `creator` | node | present on `ConstructionStepNode`, absent on `ConstructionRootNode` |
| *(any public creator attribute)* | JSON scalar / list / dict | whatever the Creator stored publicly |
| *(private attributes)* | — | **never** serialised: the encoder emits only names without a leading `_` |

### Encoding rules 🟢

```
dic = {k: v for k, v in o.__dict__.items() if not k.startswith('_')}
dic["$TYPE"] = o.__class__.__name__
```

Consequences: `_shapes_of_interest_keys` is **not** stored (the public parameter
that reconstructs it is); `_config`-style injections vanish, which is what makes
a plan portable between aircraft; `ConstructionRootNode._output_shapes` and
`JSONStepNode._to_be_injected` never appear.

### Decoding rules 🟢

| Step | Rule |
|---|---|
| 1. Marker check | a dict without `$TYPE` is returned as a plain dict |
| 2. Class resolution | `getattr(sys.modules["cad_designer.airplane.GeneralJSONEncoderDecoder"], name)` → **`AttributeError`** if absent |
| 3. Parameter selection | `**kwargs` in `__init__` ⇒ whole dict **+ all** decoder kwargs (and the parsed dict is mutated in place 🟡); otherwise the dict ∩ `__init__` parameter names, with matching decoder kwargs **overlaid on top** |
| 4. Coercion | `_coerce_params` (see below) |
| 5. Placeholders | `re.sub(r"\{(\w+)\}", …)` over already-coerced sibling values |
| 6. Construction | `cls(**intersection_dict)` |

`object_hook` fires **bottom-up**, so a node's `creator` and `successors` are
live objects before the node itself is built. 🟢

### The resolvable class universe 🟢

Exactly what `GeneralJSONEncoderDecoder.py` imports:

```python
from cad_designer.airplane.ConstructionRootNode import ConstructionRootNode
from cad_designer.airplane.ConstructionStepNode import ConstructionStepNode
from cad_designer.airplane.creator import *      # the 29 registered Creators
import cad_designer.cq_plugins                   # side effect: installs the monkey-patches
```

**Topology classes are not resolvable and never appear in a plan JSON.**
`JSONStepNode` is importable but is *not* re-exported into this namespace by
`creator/__init__.py` — 🟡 so a plan cannot reference `$TYPE: "JSONStepNode"`
unless it is imported elsewhere in the chain.

> 🔴 **BR-71 — renaming or deleting a Creator breaks every stored plan that
> references it.** Confirmed today: 9 of the 32 `$TYPE` names used by
> `components/constructions/*.json` no longer exist
> (`FullWingLoftShapeCreator`, `FullFuselageLoftShapeCreator`,
> `WingRibCageCreator`, `ReinforcementPipesCreator`, `WingOffsetCreator`,
> `MirrorShapeCreator`, `EngineMountPanelShapeCreator`,
> `CPACSTrailingEdgeDeviceCreator`, `CPACSTrailingEdgeDeviceCutOutCreator`,
> `CPACSServoCutOutCreator`), making `wings.root.json`, `fuselage.root.json` and
> `full_wing.json` undecodable. Latent — nothing under `app/` reads them.

### Type coercion contract 🟢

| Input | Annotation | Result |
|---|---|---|
| `None` | anything | passed through |
| any | key not annotated | passed through |
| `"fuselage"` | `list[...]` | `["fuselage"]` — **the character-iteration guard**, checked first |
| `""` / `"   "` | `list[...]` | `[]` |
| non-list, non-str | `list[...]` | passed through |
| `"0.1"` | `float`, `confloat`, `Factor`, `Annotated[float, …]`, `"float"` | `0.1` |
| `"0,1"` | float-ish | `0.1` |
| `"1.234,56"` | float-ish | `1234.56` (German: last separator is the decimal) |
| `"1,234.56"` | float-ish | `1234.56` (English) |
| `"12"` | `int`, `conint`, `NonNegativeInt` | `12` (via `int(float(...))`) |
| any | `bool` | `bool(value)` |
| any | `str`, `ShapeId`, `CreatorId` | `str(value)` |
| `"abc"` | `float` | ⚠ warning logged, **raw value kept** — no exception |

`_resolve_base_type` unwraps, in order: string annotations (heuristic — note
that any hint containing `"factor"` resolves to `float` 🟡),
`NewType.__supertype__`, `__origin__`/`__args__[0]` recursion, then the four
plain scalars. The `list[...]` guard **must** precede it, because
`_resolve_base_type(list[str])` would otherwise return `str`. 🟢

### Placeholder contract 🟢

| `creator_id` | Sibling values | Result |
|---|---|---|
| `"{wing_index}.loft"` | `wing_index = "main"` | `"main.loft"` |
| `"{wing_index}.loft"` | `wing_index` absent or `None` | `"{wing_index}.loft"` (verbatim) |
| `"{keys}.out"` | `keys = ["a","b"]` (list or dict) | `"{keys}.out"` (verbatim) |

### Decoder kwarg injection 🟢

The five names `construction-plans` and `cad-generation` inject:

| Kwarg | Type | Injected by |
|---|---|---|
| `wing_config` | `dict[str, WingConfiguration]` (**mm**) | `construction_plan_service.execute_plan`, `cad_service` worker |
| `fuselage_config` | `dict[str, FuselageConfiguration]` (**mm**) | `cad_service` worker |
| `printer_settings` | `Printer3dSettings` | both |
| `servo_information` | `dict[int, ServoInformation]` | both — 🔴 hard-coded `{}` on the plan path |
| `engine_information` | `EngineInformation \| None` | both — 🔴 hard-coded `None` on the plan path |
| `component_information` | `ComponentInformation \| None` | both — 🔴 hard-coded `None` on the plan path |

Injections **override** stored values of the same name in both decode branches.
`_INTERNAL_PARAMS` in `construction-plans` hides exactly these names (plus
`self`, `loglevel`, `kwargs`, `creator_id`) from the Creator Catalog. 🟢

## 4 — The topology JSON format (marker-less) 🟢

A **second, independent** system with no `$TYPE` and no shared base class:

```python
obj.__getstate__() -> dict                  # plain, JSON-safe
Class.from_json_dict(data: dict) -> Class   # @staticmethod
```

Implemented by: `WingConfiguration`, `WingSegment`, `Airfoil`, `Spare`,
`TrailingEdgeDevice`, `Turbulator`, `Servo`, `CoordinateSystem`,
`AirplaneConfiguration`, `FuselageConfiguration`.

**The two systems never mix.** A topology object reaches a running plan only as
a decoder kwarg — never embedded in the plan JSON. 🟢

### Consumers 🟢

| Consumer | Surface |
|---|---|
| `wing-design` | `GET/PUT /aeroplanes/{id}/wings/{name}/wingconfig`, `POST .../from-wingconfig` (**mm** on the wire) |
| `aeroplane-core` | `AirplaneConfiguration.to_dict()` / `save_to_json()` / `save_to_zip()` export payload |
| `cad-generation` | rebuilds a `WingConfiguration` in the worker from a pickled `AsbWingSchema`, not from this format 🟡 |

### `CoordinateSystem` — the one asymmetric case 🟢

```json
{"xDir": [...], "yDir": [...], "zDir": [...], "origin": [...], "euler_xyz": [...]}
```

`__getstate__` **emits** `euler_xyz`; `from_json_dict` **ignores** it and
recomputes from the direction vectors, defaulting each to the identity basis and
the origin to `[0,0,0]`. A hand-edited `euler_xyz` is silently discarded. 🟢

Construction-time validation: `R = matrix([xDir,yDir,zDir]).T` must satisfy
`R·Rᵀ ≈ I` **and** `det R ≈ 1` (`atol=1e-6`), else
`InvalidRotationMatrixException`. The decomposition uses
`as_euler(order.lower(), degrees=True)` — 🟡 always **extrinsic**, because the
`'XYZ'` passed by the call site is lower-cased.
`InvalidRotationOrderException` is declared and never raised. 🔴

### `AirplaneConfiguration` envelopes 🟢

```
to_dict()      → {"name": str, "total_mass_kg": float,
                  "wings": [WingConfiguration.__getstate__(), …],
                  "fuselages": [...]}          # key omitted when falsy
save_to_json() → json.dump(to_dict(), indent=4)
save_to_zip()  → temp tree with wings/ and fuselages/, one JSON per object, zipped
```

⚠ Constructor precondition: `wings` must be non-empty — `__init__` immediately
evaluates `self.wings[self._main_wing_index]` and raises `IndexError`
otherwise. 🟢
🔴 `_main_wing_index = 0` is a dormant copy of the gh-788 "first wing is the
main wing" bug; `asb_airplane` is a `cached_property` that also assigns
`self._asb_main_wing` as a side effect.

## 5 — Domain literal types 🟢

`cad_designer/airplane/types.py` — the vocabulary shared with `app/schemas/`.

| Name | Definition | Normalisation |
|---|---|---|
| `Factor` | `confloat(ge=0, le=1.0)` | — |
| `DihedralInDegrees` | `confloat(ge=-180.0, le=180.0)` | — |
| `CoordinateSystemBase` | `Literal["world","wing","root_airfoil","tip_airfoil"]` | `.lower()` |
| `WingSegmentType` | `Literal["root","segment","tip"]` | `.lower()` |
| `TipType` | `Literal["flat","round"]` | `.lower()` |
| `WingSides` | `Literal["LEFT","RIGHT","BOTH"]` | **`.upper()`** |
| `ShapeId` | `NewType("ShapeId", str)` | none — documentation only |
| `CreatorId` | `NewType("CreatorId", str)` | none — documentation only |
| `TurbulatorForm` | `Literal["zigzag","dots","thread"]` (`wing/Turbulator.py:5`) | — |

A non-string value passes through every `BeforeValidator` untouched and then
fails the `Literal` check. 🟢

## 6 — The CadQuery extension surface 🟢

Installed as a **side effect of import** — `import cad_designer.cq_plugins`.
`GeneralJSONEncoderDecoder.py:7` performs that import, so decoding a plan is
sufficient to guarantee the methods exist.

| Attached to | Name | Registered by `cq_plugins/__init__`? |
|---|---|---|
| `Workplane` | `fix_shape` | yes |
| `Workplane` | `offset3D` | yes (via the misspelled `offest3D` package) |
| `Workplane` | `display` | yes — gated by `@conditional_execute("DISPLAY_CONSTRUCTION_STEP")` |
| `Workplane` | `sewAndFix` | yes (via `sew_fix_shape`) |
| `Workplane` | `airfoil`, `wing_root_segment`, `wing_segment` | yes (via `wing`) |
| `Sketch` | `segmentToEdge` | yes |
| `Workplane` | `scaleXyz` | 🔴 **no** — the module is never imported; its implementation also has a typo'd parameter `y_sacle` |

## 7 — Environment contract 🟢

| Variable | Accepted values | Effect |
|---|---|---|
| `DISPLAY_CONSTRUCTION_STEP` | `"1"`, `"ON"`, `"TRUE"`, `"ENABLED"` — compared **case-insensitively** via `.upper()` | enables `Workplane.display`; anything else (including unset) logs a warning and returns `self` unchanged |

This is the hook [`construction-plans`](../construction-plans/contracts.md)
toggles to emit SSE `shape` events. 🔴 It is **process-global**, so two
concurrent executions in one process share it.

## Error contract 🟢

This module raises **plain Python exceptions**; it knows nothing about
`app/core/exceptions.py` or HTTP. Callers map them.

| Condition | Exception | Mapped by |
|---|---|---|
| unknown `$TYPE` | `AttributeError` | `construction-plans` → `ValidationError("Failed to decode construction plan: …")` → 422 |
| declared shape missing | `KeyError` | `construction-plans` → `ExecutionResult(status="error")` |
| too few input shapes for positional slots | `KeyError` | same |
| non-orthonormal rotation basis | `InvalidRotationMatrixException` | 🔴 unmapped — surfaces as a 500 |
| empty `wings` on `AirplaneConfiguration` | `IndexError` | 🔴 unmapped — surfaces as a 500 |
| unknown `WingConfiguration.parameters` | `ValueError` (message names `'absolute'`, a value never accepted 🔴) | 🔴 unmapped |
| uncoercible parameter value | **none** — warning logged, raw value kept | may surface later as a `TypeError` inside the Creator, or not at all |
| CadQuery absent | `ImportError` at import time | `construction-plans` returns `[]`; the CAD router is not mounted (ADR 0017) |

## Not part of this contract

- The spar sizing / solver / section-geometry algorithms, even though the files
  live under `cad_designer/airplane/geometry/` — they are **editable feature
  code** owned by [`wing-design`](../wing-design/contracts.md).
- The fuselage slicer (`cad_designer/aerosandbox/slicing.py`) →
  [`fuselage-design`](../fuselage-design/contracts.md).
- Plan CRUD, template instantiation, execution orchestration, SSE streaming,
  artefact capture and the Creator Catalog REST projection →
  [`construction-plans`](../construction-plans/contracts.md).
- The process pool, pickling boundary, tessellation and export blueprint →
  [`cad-generation`](../cad-generation/contracts.md).
- The millimetre↔metre conversion functions themselves (`app/converters/`) →
  `wing-design` / `fuselage-design`.
- Every HTTP route, MCP tool and database table in the system.
