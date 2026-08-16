# json-polymorphic-roundtrip

> Use-case specification, nested under the module
> [`cad-designer-topology`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: cad-designer-topology
> (`GeneralJSONEncoder`/`Decoder`, A second independent serialisation system),
> `_reversa_sdd/data-dictionary.md` §Plan-tree JSON envelope,
> `_reversa_sdd/domain.md` §2.10 BR-71.
>
> ⚠ `GeneralJSONEncoderDecoder.py` is **FROZEN** (ADR 0002). The spec documents
> behaviour to preserve, not code to change.

## Overview

`json-polymorphic-roundtrip` is the **persistence contract** of the CAD library:
how a live construction tree becomes JSON, how JSON becomes a live tree again,
and how runtime configuration is injected at the boundary. It is the format
behind `construction_plans.tree_json`, the shipped
`components/constructions/*.json` files, and the blueprint `cad-generation`
synthesises for an export. It also defines a **second, entirely separate**
marker-less format for topology objects — the one behind the `/wingconfig`
endpoints. 🟢

Its defining property is that **the compatibility contract is a Python class
name**. There is no version field, no registry and no deprecation path. 🟢

## Responsibilities

- Encode a construction tree to JSON, emitting **only public attributes** plus a
  `$TYPE` discriminator. 🟢
- Decode `$TYPE` back to a live class by name, against exactly one module
  namespace. 🟢
- Select the constructor arguments from the stored dict, with two different
  strategies depending on whether the class accepts `**kwargs`. 🟢
- **Inject runtime configuration** (`wing_config`, `printer_settings`,
  `servo_information`, `engine_information`, `component_information`) into
  decoded objects, overriding stored values. 🟢
- Coerce JSON strings to the annotated scalar type, unwrapping `NewType`,
  `Annotated`, pydantic constrained types and string annotations. 🟢
- Normalise numeric strings **locale-aware**, accepting German and English
  decimal formats. 🟢
- Guard against a bare string being iterated character-by-character when the
  annotation is a list type. 🟢
- Substitute `{placeholder}` tokens in `creator_id` from sibling parameter
  values. 🟢
- Define the **second, marker-less** topology format
  (`__getstate__` / `from_json_dict`) and keep it strictly separate from the
  plan format. 🟢

**Explicitly NOT this use case's responsibility:** the Creator contract and tree
traversal that the decoded objects then execute (→
[`../creator-execution-model/`](../creator-execution-model/requirements.md)), the
geometric meaning of the topology objects being serialised (→
[`../wingconfiguration-coordinate-system/`](../wingconfiguration-coordinate-system/requirements.md)),
plan CRUD, the `_migrate_tree_json` legacy-root rewrite and the `_rewrite_export_paths`
pre-pass (→ [`construction-plans`](../../construction-plans/requirements.md)),
the blueprint `cad-generation` synthesises (→
[`cad-generation`](../../cad-generation/requirements.md)), and the
`construction_plans` table itself.

## Business Rules

> IDs are inherited verbatim from [`../requirements.md`](../requirements.md).

- **BR-CT14 — Only public attributes are serialised.** 🟢
  `GeneralJSONEncoder.default` (`GeneralJSONEncoderDecoder.py:20-25`):

  ```python
  dic = {k: v for k, v in o.__dict__.items() if not k.startswith('_')}
  dic[GeneralJSONEncoder.JSON_CLASS_TYPE_ID] = o.__class__.__name__
  ```

  `JSON_CLASS_TYPE_ID = '$TYPE'` (l.18). This is **why** the authoring contract
  requires runtime-injected config to be stored as `self._private`: a public
  field would be written into the stored plan and then shadowed by the injection
  at decode time. Consequences: `_shapes_of_interest_keys` is not stored (the
  public parameter that reconstructs it is), `ConstructionRootNode._output_shapes`
  and `JSONStepNode._to_be_injected` never appear.
- **BR-CT15 — `$TYPE` resolves against exactly one module namespace.** 🟢
  `object_hook` does
  `getattr(sys.modules[__name__], dic["$TYPE"])` (l.196-198), where `__name__` is
  `cad_designer.airplane.GeneralJSONEncoderDecoder`. The resolvable universe is
  therefore precisely what that module imports (l.4-7):

  ```python
  from cad_designer.airplane.ConstructionRootNode import ConstructionRootNode
  from cad_designer.airplane.ConstructionStepNode import ConstructionStepNode
  from cad_designer.airplane.creator import *
  import cad_designer.cq_plugins            # side effect: installs the monkey-patches
  ```

  An unknown name raises `AttributeError`. **Topology classes are not resolvable
  and never appear in a plan JSON.** 🟡 `JSONStepNode` is importable but is not
  re-exported into this namespace by `creator/__init__.py`, so a plan cannot
  reference `$TYPE: "JSONStepNode"` unless it is imported elsewhere in the chain.
- **BR-71 — Renaming or deleting a Creator invalidates every stored plan that
  references it.** 🟢 (global rule, `domain.md` §2.10) A direct corollary of
  BR-CT15, and the reason `_creator_template.py` makes subpackage registration a
  mandatory step.
- **BR-CT16 — `**kwargs` in `__init__` switches the decode contract.** 🟢
  (l.199-210)

  ```
  if "kwargs" in inspect.signature(cls.__init__).parameters:
      intersection_dict = dic
      intersection_dict.update(self.kwargs)          # whole dict + ALL injections
  else:
      intersection = {k: self.kwargs[k] for k in self.kwargs.keys() & init_params.keys()}
      intersection_dict = {k: dic[k]    for k in dic.keys()        & init_params.keys()}
      intersection_dict.update(intersection)         # injections WIN over stored values
  ```

  In both branches injected kwargs **override** stored values of the same name.
  🟡 The `**kwargs` branch mutates the parsed `dic` in place, making
  `object_hook` impure. The set-intersection in the other branch is what lets a
  plan survive a Creator gaining or losing an optional parameter — an unknown
  stored key is **dropped**, not passed through to a `TypeError`.
- **BR-CT17 — JSON strings are coerced to the annotated scalar type,
  locale-aware.** 🟢 `_coerce_params` (l.125-176) reads
  `cls.__init__.__annotations__` minus `"return"`, returning `params` unchanged
  if the class has no annotations at all. Per key: `None` values and unannotated
  keys pass through; otherwise `_resolve_base_type` (l.28-84) resolves the
  target, unwrapping — in order — **string** annotations (from
  `from __future__ import annotations`), `NewType.__supertype__`,
  `__origin__`/`__args__[0]` recursion, then the four plain scalars
  (`float`, `int`, `bool`, `str`). Coercion:

  ```
  float → float(_normalize_numeric_string(value))
  int   → int(float(_normalize_numeric_string(value)))
  bool  → bool(value)
  str   → str(value)
  ```

  A `ValueError` / `TypeError` logs
  `"Type coercion failed for %s.%s: value=%r, expected=%s (%s)"` and **keeps the
  raw value** — decoding never aborts on a bad field.
  🟡 The string branch is a case-insensitive heuristic: `"confloat…"` → `float`,
  `"nonnegativeint"`/`"conint…"` → `int`, `"creatorid"`/`"shapeid"` → `str`, and
  **any** hint containing `"factor"` → `float`.
- **BR-CT18 — A `list[...]` annotation receiving a bare string is wrapped, never
  iterated.** 🟢 (l.144-152)

  ```
  _is_list_type(hint) and isinstance(value, str)      → [value] if value.strip() else []
  _is_list_type(hint) and not isinstance(value, list) → passed through unchanged
  ```

  This guard **must run before** `_resolve_base_type`, because
  `_resolve_base_type(list[str])` would otherwise return `str` via its
  `__args__[0]` recursion and stringify the list. `_is_list_type` (l.87-92)
  handles both real annotations (`__origin__ is list`) and string annotations
  (`"list["` prefix or exactly `"list"`).
- **BR-CT19 — `creator_id` placeholders resolve from sibling parameters.** 🟢
  (l.212-223) `re.sub(r"\{(\w+)\}", …)` runs **after** coercion, substituting
  from the same object's already-coerced values. A parameter that is missing,
  `None`, a `dict` or a `list` leaves the placeholder **verbatim**, producing a
  step whose identifier literally contains braces.
- **BR-CT20 — Topology objects use a second, marker-less serialisation
  system.** 🟢 Every topology class implements `__getstate__() -> dict` plus
  `@staticmethod from_json_dict(data) -> Self` with **no `$TYPE`**:
  `WingConfiguration`, `WingSegment`, `Airfoil`, `Spare`, `TrailingEdgeDevice`,
  `Turbulator`, `Servo`, `CoordinateSystem`, `AirplaneConfiguration`,
  `FuselageConfiguration`. This is the format behind the `/wingconfig` endpoints
  and `AirplaneConfiguration.to_dict()` / `save_to_json` / `save_to_zip`.
  **The two systems never mix**: a topology object reaches a running plan only
  as a **decoder kwarg**.
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

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-JS-01 | Encode any construction-tree object, emitting only public attributes plus `$TYPE` | Must | A creator holding `self._config` round-trips with no underscore-prefixed key in the JSON |
| RF-JS-02 | Set `$TYPE` to the class `__name__` | Must | A `ConstructionStepNode` serialises with `"$TYPE": "ConstructionStepNode"` |
| RF-JS-03 | Return a dict without `$TYPE` unchanged during decode | Must | A plain nested JSON object (e.g. a parameter dict) survives as a dict |
| RF-JS-04 | Resolve `$TYPE` by name against the encoder/decoder module namespace | Must | Every registered Creator decodes; an unregistered or removed name raises `AttributeError` |
| RF-JS-05 | Pass the whole dict plus all decoder kwargs when `__init__` accepts `**kwargs` | Must | A Creator with `**kwargs` receives `wing_config` |
| RF-JS-06 | Otherwise intersect the dict with the `__init__` parameter names and overlay matching decoder kwargs | Must | A Creator without `**kwargs` receives only its declared parameters |
| RF-JS-07 | Let injected kwargs override stored values of the same name | Must | A stored `wing_config` key is replaced by the injected object |
| RF-JS-08 | Drop stored keys the constructor does not declare | Must | A plan written against an older Creator with an extra field still decodes |
| RF-JS-09 | Split the decoder's own kwargs from the injection payload | Must | `object_pairs_hook` reaches `JSONDecoder`; `wing_config` does not |
| RF-JS-10 | Coerce annotated scalar parameters from JSON strings | Must | `"0.1"` on a `float` parameter becomes `0.1` |
| RF-JS-11 | Unwrap `NewType`, `Annotated`, `confloat` and string annotations when resolving the target type | Must | A `Factor`-annotated parameter coerces to `float`; a `ShapeId` to `str` |
| RF-JS-12 | Normalise numeric strings locale-aware | Must | `"0,1"`→`0.1`; `"1.234,56"`→`1234.56`; `"1,234.56"`→`1234.56`; `"1234"` unchanged |
| RF-JS-13 | Wrap a bare string into a one-element list when the annotation is a list type | Must | `"fuselage"` becomes `["fuselage"]`; `""` becomes `[]` |
| RF-JS-14 | Pass through non-list, non-string values for list annotations | Should | A stored `null` or number on a list parameter is not wrapped |
| RF-JS-15 | Pass through `None` values and unannotated keys | Must | A `None` default is not coerced to `0.0` or `"None"` |
| RF-JS-16 | Log and preserve on coercion failure, never raise | Must | `"abc"` on a `float` logs a warning naming class and parameter and survives verbatim |
| RF-JS-17 | Substitute `{param}` placeholders in `creator_id` from coerced sibling values | Should | `"{wing_index}.loft"` with `wing_index = "main"` yields `"main.loft"` |
| RF-JS-18 | Leave unresolvable placeholders verbatim | Should | `"{missing}.loft"` is unchanged; a `list`- or `dict`-valued parameter does not interpolate |
| RF-JS-19 | Provide `__getstate__` / `from_json_dict` on every topology class, with no type marker | Must | A `WingConfiguration` round-trips through the pair; the dict has no `$TYPE` |
| RF-JS-20 | Keep topology objects out of plan JSON, injecting them only as decoder kwargs | Must | No stored plan contains a serialised topology object |
| RF-JS-21 | Install the CadQuery extensions as a side effect of importing the serialisation module | Should | Decoding a plan is sufficient for `Workplane.sewAndFix` to exist |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Robustness | Decoding never aborts on one bad field — coercion logs and preserves | `GeneralJSONEncoderDecoder.py:169-175` | 🟢 |
| Robustness | A plan survives a Creator gaining or losing an optional parameter | set-intersection l.206-208 | 🟢 |
| Compatibility | Stored plans are versionless; class **names** are the entire compatibility contract | l.196-198; BR-71 | 🟢 |
| Compatibility | Locale-aware numeric parsing accepts German and English decimal formats from the frontend | `_normalize_numeric_string` l.95-122 | 🟢 |
| Correctness | The list guard prevents a shape key being iterated character-by-character — a silent, hard-to-diagnose corruption | l.144-149 | 🟢 |
| Correctness | Runtime config is injected, never persisted, so a plan is portable between aircraft | encoder l.22 + injection l.203/210 | 🟢 |
| Security | 🟡 `$TYPE` resolution is confined to one module namespace, which bounds arbitrary-class instantiation to the registered Creators | l.196-198 | 🟡 |
| Diagnosability | The coercion warning names the class, the parameter, the value and the expected type | l.171-174 | 🟢 |
| Diagnosability | 🔴 An unknown `$TYPE` raises a bare `AttributeError` naming only the attribute, with no plan or step context | l.198 | 🔴 |
| Purity | 🟡 `object_hook` mutates the parsed dict in the `**kwargs` branch | l.202-203 | 🟡 |

## Acceptance Criteria

```gherkin
Feature: Encoding a construction tree

  Scenario: Private attributes are excluded
    Given a creator holding a public "thickness" and a private "_wing_config"
    When the tree is encoded
    Then the JSON contains "thickness"
    And it contains no key starting with an underscore

  Scenario: Every node carries its class name
    Given a tree of a root node and two step nodes
    When the tree is encoded
    Then each node object carries a $TYPE equal to its class name
    And the root's JSON has no "creator" key

Feature: Decoding a construction tree

  Scenario: A tree round-trips
    Given an encoded construction tree
    When it is decoded with the required runtime config
    Then the reconstructed tree produces the same shape keys as the original

  Scenario: A dict without a type marker survives as a dict
    Given a plan containing a nested parameter object with no $TYPE
    When the plan is decoded
    Then that object is still a plain dict

  Scenario: A removed Creator makes the plan undecodable
    Given a stored plan referencing $TYPE "WingRibCageCreator"
    And no class of that name exists in the resolvable namespace
    When the plan is decoded
    Then an AttributeError is raised

  Scenario: A topology class cannot be named as a $TYPE
    Given a stored plan referencing $TYPE "WingConfiguration"
    When the plan is decoded
    Then an AttributeError is raised
    # Topology classes are deliberately not in the resolvable namespace

Feature: Parameter selection and injection

  Scenario: A creator accepting kwargs receives all injections
    Given a creator whose __init__ accepts **kwargs
    When the plan is decoded with wing_config and printer_settings
    Then the creator receives both

  Scenario: A creator not accepting kwargs receives only declared parameters
    Given a creator declaring only creator_id and thickness
    When the plan is decoded with wing_config
    Then the creator receives creator_id and thickness only

  Scenario: An injection overrides a stored value
    Given a stored plan containing a wing_config key
    And a decoder injecting a different wing_config
    When the plan is decoded
    Then the injected object wins

  Scenario: An unknown stored key is dropped
    Given a stored plan carrying a parameter the current creator no longer declares
    When the plan is decoded
    Then the creator is constructed without it
    And no TypeError is raised

  Scenario: Decoder options do not leak into constructors
    Given a decoder built with both object_pairs_hook and wing_config
    When a plan is decoded
    Then JSONDecoder receives object_pairs_hook
    And the creators receive wing_config

Feature: Type coercion

  Scenario: A plain numeric string is coerced
    Given a creator parameter annotated as float
    And the stored value is the string "0.1"
    When the plan is decoded
    Then the parameter value is 0.1

  Scenario: A German decimal string is coerced correctly
    Given a creator parameter annotated as float
    And the stored value is the string "1.234,56"
    When the plan is decoded
    Then the parameter value is 1234.56

  Scenario: An English thousands-separated string is coerced correctly
    Given a creator parameter annotated as float
    And the stored value is the string "1,234.56"
    When the plan is decoded
    Then the parameter value is 1234.56

  Scenario: A constrained or aliased annotation is unwrapped
    Given a creator parameter annotated as Factor
    And the stored value is the string "0,25"
    When the plan is decoded
    Then the parameter value is 0.25

  Scenario: An uncoercible value does not abort the decode
    Given a creator parameter annotated as float
    And the stored value is the string "not-a-number"
    When the plan is decoded
    Then a warning is logged naming the class and the parameter
    And the parameter keeps the raw string value
    And the object is still constructed

  Scenario: A None value is left alone
    Given a creator parameter annotated as float whose stored value is null
    When the plan is decoded
    Then the parameter value is None

  Scenario: A bare string for a list parameter is wrapped
    Given a creator parameter annotated as list[ShapeId]
    And the stored value is the string "fuselage"
    When the plan is decoded
    Then the parameter value is the list ["fuselage"]

  Scenario: An empty string for a list parameter becomes an empty list
    Given a creator parameter annotated as list[ShapeId]
    And the stored value is the string ""
    When the plan is decoded
    Then the parameter value is the empty list

Feature: Creator id placeholders

  Scenario: A placeholder resolves from a sibling value
    Given a creator_id of "{wing_index}.loft" and a wing_index of "main"
    When the plan is decoded
    Then the creator_id is "main.loft"

  Scenario: An unresolvable placeholder survives verbatim
    Given a creator_id of "{missing}.loft" and no missing parameter
    When the plan is decoded
    Then the creator_id is still "{missing}.loft"

  Scenario: A list-valued parameter does not interpolate
    Given a creator_id of "{keys}.out" and a keys parameter of ["a","b"]
    When the plan is decoded
    Then the creator_id is still "{keys}.out"

Feature: The topology format

  Scenario: A wing configuration round-trips without a type marker
    Given a WingConfiguration in millimetres
    When __getstate__ is serialised and passed to from_json_dict
    Then the reconstructed object is equivalent
    And the serialised dict contains no $TYPE key

  Scenario: The two systems stay separate
    Given a construction plan referencing a wing by name
    When the plan is encoded
    Then no serialised topology object appears anywhere in it
    And the wing reaches the creators only as an injected wing_config
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Encode/decode round trip (RF-JS-01…RF-JS-04) | Must | The only persistence format for `construction_plans.tree_json`; a mismatch makes every stored plan unloadable |
| Private-attribute exclusion (RF-JS-01) | Must | The mechanism that keeps runtime config out of storage and makes a plan portable between aircraft |
| Parameter selection and injection (RF-JS-05…RF-JS-08) | Must | Without injection no Creator can reach a wing; without the intersection every Creator signature change breaks stored plans |
| Decoder kwargs split (RF-JS-09) | Must | Otherwise `wing_config` is passed to `JSONDecoder` and raises |
| Scalar coercion (RF-JS-10, RF-JS-11, RF-JS-15) | Must | The frontend submits form values as strings; without it every numeric parameter arrives as a `str` |
| The list guard (RF-JS-13) | Must | Without it a shape key is iterated character-by-character — a silent corruption with no error |
| Locale normalisation (RF-JS-12) | Must | German-format decimals reach the API from the frontend; `float("0,1")` would raise |
| Non-fatal coercion failure (RF-JS-16) | Must | One bad field must not make an entire stored plan unloadable |
| Topology `__getstate__` / `from_json_dict` (RF-JS-19, RF-JS-20) | Must | The `/wingconfig` endpoints and the whole `wing-design` round-trip ride on it |
| Placeholder substitution (RF-JS-17, RF-JS-18) | Should | A convenience for authored plans; a literal id always works |
| List pass-through for non-strings (RF-JS-14) | Should | Defensive; a well-formed plan never hits it |
| Plugin installation side effect (RF-JS-21) | Should | Convenient and relied upon, but a consumer could import the plugins itself |
| A schema version on stored plans | Won't (today) | Deliberately absent — see the 🔴 gap; adding one is a design change, not a reproduction |
| Repairing the three undecodable plan JSONs | Won't (this module) | Authored by the `test/` root, unread by `app/`; ownership unresolved (see `tasks.md` TM-JS-01) |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `cad_designer/airplane/GeneralJSONEncoderDecoder.py` (224 l.) | `GeneralJSONEncoder.default`, `JSON_CLASS_TYPE_ID`, `GeneralJSONDecoder.__init__`, `object_hook`, `_resolve_base_type`, `_is_list_type`, `_normalize_numeric_string`, `_coerce_params` | 🟢 read-only (frozen) |
| `cad_designer/airplane/creator/__init__.py` + the five subpackage `__init__.py` files | the re-export lists that populate the resolvable namespace | 🟢 |
| `cad_designer/airplane/ConstructionRootNode.py`, `ConstructionStepNode.py` | the two node classes imported into the resolvable namespace | 🟢 |
| `cad_designer/airplane/JSONStepNode.py` | decodes a sub-tree with `GeneralJSONDecoder`; 🟡 not itself re-exported into the resolvable namespace | 🟢 |
| `cad_designer/airplane/aircraft_topology/**` | `__getstate__` / `from_json_dict` on the ten topology classes | 🟢 read-only |
| `components/constructions/*.json` | 8 shipped plan files; 3 undecodable (BR-CT28) | 🟢 by scan |
| `app/services/construction_plan_service.py` | the decode call site and its injected kwargs — owned by [`construction-plans`](../../construction-plans/requirements.md) | 🟢 cross-referenced |
| `app/services/cad_service.py` | `build_wing_blueprint` synthesises this dialect in memory — owned by [`cad-generation`](../../cad-generation/requirements.md) | 🟢 cross-referenced |
