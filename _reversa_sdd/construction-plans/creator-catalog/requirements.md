# creator-catalog

> Use-case specification, nested under the module
> [`construction-plans`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: construction-plans
> (Creator Catalog), `_reversa_sdd/data-dictionary.md` §Construction-plan
> schemas, `_reversa_sdd/flowcharts/construction-plans.md` §4, ADR 0017.
>
> **Boundary note.** The module's suggested slice list originally named
> `spar-plan/` here. The spar pipeline (`spar_sizing`, `spar_solver`,
> `spar_plan_service`, `spar_insert_service`, `section_geometry`) is owned by
> **`wing-design`** and already specified at
> `_reversa_sdd/wing-design/spar-sizing/`; `code-analysis.md` states the
> non-duplication rule explicitly. `creator-catalog` takes its place.

## Overview

`creator-catalog` is the **reflection layer** that lets a human build a plan
without reading the CAD library's source: it walks the live
`AbstractShapeCreator` subclass tree and, per class, derives a constructor
parameter list with resolved type strings and literal options, docstring-derived
descriptions and outputs, a suggested id template and a category. It is the only
producer of the frontend's Creator gallery, and it is the module's most visible
platform guard — on a machine without CadQuery it answers with an empty list
rather than an error. 🟢

## Responsibilities

- Walk `AbstractShapeCreator.__subclasses__()` recursively, skipping the three
  construction-tree classes while still recursing through them. 🟢
- Derive each Creator's author-facing parameters from `inspect.signature`, minus
  the framework and decoder-injected arguments. 🟢
- Render type annotations to strings that survive generics and drop internal
  module prefixes. 🟢
- Extract allowed values from `Literal` annotations in all their wrappings. 🟢
- Parse the class docstring into a summary, per-parameter descriptions and a list
  of output shape keys. 🟢
- Assign a category from the module path and sort the result deterministically. 🟢
- Degrade to an empty catalog, never an error, when the CAD library cannot be
  imported. 🟢

**Explicitly NOT this use case's responsibility:** the `AbstractShapeCreator`
contract itself, the `suggested_creator_id` placeholder convention and the
docstring conventions Creator authors are asked to follow (→
`cad-designer-topology`, frozen per ADR 0002 — this slice only *reads* them);
storing or validating plans (→
[`../plan-template-lifecycle/`](../plan-template-lifecycle/requirements.md));
decoding and running a tree (→
[`../plan-execution/`](../plan-execution/requirements.md)); uploaded part files
(→ [`../construction-parts/`](../construction-parts/requirements.md)); and the
gallery UI that renders this payload (→ `frontend-workbench`).

## Business Rules

> IDs are inherited verbatim from [`../requirements.md`](../requirements.md).

- **BR-CP14 — The catalog is pure reflection over the live subclass tree.** 🟢
  `_collect_creators` (`construction_plan_service.py:507-553`) recurses
  `AbstractShapeCreator.__subclasses__()`. `ConstructionRootNode`,
  `ConstructionStepNode` and `JSONStepNode` are **skipped as entries but still
  recursed through**, so a Creator that happens to subclass one of them is still
  listed. Results are sorted by `(category, class_name)`.
- **BR-CP14a — Registration is the visibility rule.** 🟢 A subclass only exists
  in `__subclasses__()` once its module has been imported, and the catalog's
  import is `cad_designer.airplane.creator`, whose `__init__.py` re-exports each
  subpackage. A Creator missing from its subpackage `__init__.py` is therefore
  **invisible in the gallery and undecodable in a plan** — the same registration
  requirement observed from two sides (see `cad-designer-topology`, BR-71).
- **BR-CP15 — Internal constructor parameters are hidden.** 🟢

  ```
  _INTERNAL_PARAMS = {self, loglevel, kwargs, creator_id,
                      wing_config, printer_settings, servo_information,
                      engine_information, component_information}     (l.257-268)
  ```

  This is exactly *framework arguments* ∪ *decoder-injected kwargs*, so the
  gallery shows only what a human must supply.
- **BR-CP16 — Generic annotations are resolved before `__name__`.** 🟢
  `_type_to_str` (l.423-436) handles generic aliases **first**, because
  `list[ShapeId].__name__` is just `"list"` and would lose the subscript that
  tells the UI it needs a multi-select. The `typing.` and
  `cad_designer.airplane.types.` prefixes are then stripped, so a caller sees
  `Optional[float]` and `WingSides`, not `typing.Optional[float]` and
  `cad_designer.airplane.types.WingSides`.
- **BR-CP16a — Literal options are unwrapped through every wrapping.** 🟢
  `_extract_literal_values` (l.450-480) handles `Literal`,
  `Optional[Literal]`, `Annotated[Literal]` and nested unions, flattening them
  into a plain `list[str]`. A non-literal parameter yields `None`, not `[]`.
- **BR-CP17 — Human-readable metadata is parsed out of docstrings.** 🟢
  - `description` — the **first line** of the class docstring.
  - per-parameter `description` — from the `Attributes:` block, parsed by
    `_parse_docstring_attributes` (l.330-359) with the regex
    `(\w+)\s*\([^)]*\)\s*:\s*(.*)`, i.e. `name (type): text`. The declared type in
    the parentheses is **discarded** — the real type comes from the signature.
  - `outputs` — from the `Returns:` block via `_parse_docstring_returns`
    (l.362-403), producing keys such as `{id}` and `{id}.cape`.
  - `suggested_id` — the class attribute `suggested_creator_id`, which may itself
    contain `{param}` placeholders that the decoder later substitutes from
    sibling parameter values.
  - `category` — from the module path via `_CATEGORY_MAP` (l.406-420):
    `.creator.wing` → `wing`, likewise `fuselage`, `cad_operations`,
    `export_import`, `components`; anything else → `"other"`.
- **BR-CP18 — An absent CAD kernel yields an empty catalog, never an error.** 🟢
  `list_creators` (l.483-504) wraps the `cad_designer` import and returns `[]` on
  `ImportError` — the `linux/aarch64` platform guard of ADR 0017. The route still
  answers **200**; it never 500s and never 503s.
- **BR-CP18a — Route ordering is load-bearing.** 🟢
  `GET /construction-plans/creators` is declared **before**
  `GET /construction-plans/{plan_id}`, with an in-code comment saying so
  (`construction_plans.py:51-59`). Reversed, the literal `"creators"` would be
  captured as a `plan_id` and the catalog would be unreachable.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-CC-01 | List every registered Creator class | Must | `GET /construction-plans/creators` → 200 with one entry per registered subclass |
| RF-CC-02 | Skip the three construction-tree classes but recurse through them | Must | `ConstructionRootNode`, `ConstructionStepNode` and `JSONStepNode` are absent; a Creator subclassing one of them is present |
| RF-CC-03 | Sort deterministically by `(category, class_name)` | Should | Two consecutive calls return identical ordering |
| RF-CC-04 | Expose constructor parameters with name, required flag and default | Must | A parameter with no default reports `required: true` and `default: null` |
| RF-CC-05 | Hide framework and injected parameters | Must | No entry exposes `creator_id`, `loglevel`, `wing_config`, `printer_settings`, `servo_information`, `engine_information` or `component_information` |
| RF-CC-06 | Render generic annotations without losing the subscript | Must | `list[ShapeId]` renders as `list[ShapeId]`, not `list` |
| RF-CC-07 | Strip internal module prefixes from type strings | Should | No type string contains `typing.` or `cad_designer.airplane.types.` |
| RF-CC-08 | Extract `Literal` values through `Optional` and `Annotated` wrappings | Must | A `WingSides` parameter reports `["LEFT","RIGHT","BOTH"]`; an `Optional[Literal[...]]` reports the same values |
| RF-CC-09 | Report `null` options for a non-literal parameter | Should | A `float` parameter reports `options: null`, not `[]` |
| RF-CC-10 | Use the first docstring line as the class description | Should | A Creator with a multi-line docstring reports only its first line |
| RF-CC-11 | Parse per-parameter descriptions from the `Attributes:` block | Should | A documented parameter carries its text; an undocumented one carries `null` |
| RF-CC-12 | Parse output shape keys from the `Returns:` block | Should | A Creator documenting `{id}.cape` reports that key with its description |
| RF-CC-13 | Expose `suggested_creator_id` verbatim, placeholders included | Should | `"{wing_index}.vase_wing"` is returned unresolved |
| RF-CC-14 | Assign a category from the module path | Must | A Creator under `.creator.wing` reports `wing`; an unmapped path reports `other` |
| RF-CC-15 | Answer with an empty list when `cad_designer` cannot be imported | Must | With the import failing the route returns 200 and `[]` |
| RF-CC-16 | Survive a Creator with no docstring | Should | `description` and every parameter description are `null`; `outputs` is `[]`; no exception |
| RF-CC-17 | Keep `/creators` reachable ahead of `/{plan_id}` | Must | `GET /construction-plans/creators` returns a list, not an int-parse failure |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Portability | The catalog degrades to `[]` rather than a 500 or 503 when the CAD library is unavailable | `construction_plan_service.py:483-504` (ADR 0017) | 🟢 |
| Determinism | Output ordering is fixed by an explicit sort, not by subclass-registration order | `_collect_creators:507-553` | 🟢 |
| Robustness | Docstring parsing must tolerate absent, empty and unconventional docstrings | `_parse_docstring_attributes:330-359`, `_parse_docstring_returns:362-403` | 🟡 |
| Correctness | Type rendering must handle generics before falling back to `__name__`, or the subscript is lost | `_type_to_str:423-436` (explicit ordering in the code) | 🟢 |
| Maintainability | The gallery is generated, so a new Creator needs no catalog change — only registration in its subpackage `__init__.py` | `list_creators:483-504` | 🟢 |
| Coupling | 🟡 The catalog's usefulness depends on docstring conventions that are **not** enforced anywhere — a Creator author can silently ship an undocumented parameter | `_creator_template.py` conventions; no validation | 🟡 |

## Acceptance Criteria

```gherkin
Feature: Creator reflection

  Scenario: Registered Creators are listed with their parameters
    Given the cad_designer Creator subpackages are importable
    When I GET /construction-plans/creators
    Then the response status is 200
    And every registered Creator subclass appears exactly once
    And the list is sorted by category then class name

  Scenario: The construction-tree classes are excluded
    Given ConstructionRootNode, ConstructionStepNode and JSONStepNode are subclasses
    When I GET /construction-plans/creators
    Then none of those three names appears in the list

  Scenario: A Creator subclassing a skipped class is still listed
    Given a Creator class whose base is ConstructionStepNode
    When I GET /construction-plans/creators
    Then that Creator appears in the list

  Scenario: Framework and injected parameters are hidden
    Given a Creator whose __init__ takes creator_id, loglevel and wing_config
    When I GET /construction-plans/creators
    Then none of those three parameters is exposed

Feature: Type and option rendering

  Scenario: A generic annotation keeps its subscript
    Given a Creator parameter annotated list[ShapeId]
    When I GET /construction-plans/creators
    Then the parameter type is "list[ShapeId]"

  Scenario: Internal prefixes are stripped
    Given a Creator parameter annotated cad_designer.airplane.types.WingSides
    When I GET /construction-plans/creators
    Then the type string contains no module prefix

  Scenario: Literal values become options
    Given a Creator parameter annotated WingSides
    When I GET /construction-plans/creators
    Then options is ["LEFT", "RIGHT", "BOTH"]

  Scenario: An optional literal still yields its values
    Given a Creator parameter annotated Optional[Literal["flat", "round"]]
    When I GET /construction-plans/creators
    Then options is ["flat", "round"]

  Scenario: A non-literal parameter has no options
    Given a Creator parameter annotated float
    When I GET /construction-plans/creators
    Then options is null

Feature: Docstring-derived metadata

  Scenario: The first docstring line becomes the description
    Given a Creator whose docstring has a summary line and a longer body
    When I GET /construction-plans/creators
    Then description is exactly the first line

  Scenario: Attributes entries become parameter descriptions
    Given a Creator docstring with "offset (float): distance in millimetres"
    When I GET /construction-plans/creators
    Then the offset parameter carries that description
    And its type comes from the signature, not from the docstring

  Scenario: Returns entries become output keys
    Given a Creator docstring documenting "{id}.cape"
    When I GET /construction-plans/creators
    Then outputs contains the key "{id}.cape" with its description

  Scenario: A Creator with no docstring does not break the catalog
    Given a Creator class with no docstring
    When I GET /construction-plans/creators
    Then that entry has a null description and an empty outputs list
    And no error is raised

Feature: Platform degradation and routing

  Scenario: An unavailable CAD library yields an empty catalog
    Given cad_designer cannot be imported
    When I GET /construction-plans/creators
    Then the response status is 200
    And the body is an empty list

  Scenario: The catalog route is not shadowed by the plan-id route
    Given both /construction-plans/creators and /construction-plans/{plan_id} exist
    When I GET /construction-plans/creators
    Then the response is the Creator list
    And not a 422 from parsing "creators" as an integer
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Listing registered Creators with parameters (RF-CC-01/RF-CC-04) | Must | Without it the plan editor cannot offer a single step |
| Skipping the tree classes (RF-CC-02) | Must | Listing them would let a user nest a root inside a step and produce an undecodable plan |
| Hiding internal parameters (RF-CC-05) | Must | Exposing `wing_config` would invite a user to supply a value the decoder overwrites anyway |
| Generic-safe type rendering (RF-CC-06) | Must | A lost subscript changes the input control the UI renders |
| Literal options (RF-CC-08) | Must | The difference between a free-text field and a valid enum selection |
| Empty-list platform guard (RF-CC-15) | Must | The single behaviour that keeps the workbench usable on `linux/aarch64` |
| Route ordering (RF-CC-17) | Must | A one-line mistake makes the whole catalog unreachable |
| Category assignment (RF-CC-14) | Must | The gallery groups by it; `other` is the documented catch-all |
| Deterministic ordering (RF-CC-03) | Should | Stable UI and diffable snapshots; not a correctness issue |
| Prefix stripping (RF-CC-07) | Should | Readability of the rendered type |
| Docstring-derived description, attributes and outputs (RF-CC-10…RF-CC-12) | Should | Documentation quality; a Creator remains usable without them |
| `suggested_creator_id` (RF-CC-13) | Should | An ergonomic default for the id field |
| Null options for non-literals (RF-CC-09) | Should | Lets the UI distinguish "no constraint" from "an empty enum" |
| Tolerating an undocumented Creator (RF-CC-16) | Should | One malformed docstring must not empty the whole gallery |
| Validating that Creators follow the docstring conventions | **Won't** | The conventions live in `_creator_template.py` and are enforced nowhere; adding enforcement is a `cad-designer-topology` decision, and that layer is frozen (ADR 0002) |
| Listing Creators from a module that was never imported | **Won't** | Impossible by construction — `__subclasses__()` only sees imported classes; registration in the subpackage `__init__.py` is the contract |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/construction_plan_service.py` | `list_creators` (l.483-504), `_collect_creators` (l.507-553), `_INTERNAL_PARAMS` (l.257-268), `_parse_docstring_attributes` (l.330-359), `_parse_docstring_returns` (l.362-403), `_CATEGORY_MAP` (l.406-420), `_type_to_str` (l.423-436), `_extract_literal_values` (l.450-480) | 🟢 |
| `app/api/v2/endpoints/construction_plans.py` | `list_creators` (l.53-65) and its declaration order (l.51-59) | 🟢 |
| `app/schemas/construction_plan.py` | `CreatorParam` (l.68), `CreatorOutput` (l.79), `CreatorInfo` (l.86) | 🟢 |
| `cad_designer/airplane/AbstractShapeCreator.py` | the reflected base class — specified in `cad-designer-topology` (frozen) | 🟢 cross-reference |
| `cad_designer/airplane/creator/**` | the 29 registered Creators and their `__init__.py` re-exports — specified in `cad-designer-topology` | 🟢 cross-reference |
| `cad_designer/airplane/creator/_creator_template.py` | the docstring and `suggested_creator_id` conventions this slice parses | 🟢 cross-reference |
