# creator-execution-model

> Use-case specification, nested under the module
> [`cad-designer-topology`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: cad-designer-topology
> (`AbstractShapeCreator`, The construction tree, Creator inventory),
> `_reversa_sdd/data-dictionary.md` §Construction-tree classes.
>
> ⚠ Frozen layer (ADR 0002) — behaviour to preserve, not code to change.

## Overview

`creator-execution-model` is the **execution engine** of the CAD library: the
contract every shape-producing class implements, the protocol by which a step
receives the shapes it needs from earlier steps, and the tree traversal that
sequences them. It is a flat string-keyed shape registry threaded through a
depth-first walk — no object graph, no dependency solver, no scheduler. 🟢

## Responsibilities

- Define `AbstractShapeCreator`: a **template method** (`create_shape`) with a
  single abstract subclass hook (`_create_shape`). 🟢
- Resolve a step's declared upstream shapes **by name** from the global
  registry, raising a `KeyError` that names the step when one is missing. 🟢
- Resolve **positional** (`None`) slots from the ordered `input_shapes` dict,
  most significant last, raising before lookup when there are too few. 🟢
- Adjust the **root** logger level for the duration of a step and restore it. 🟢
- Define the **output-key convention** and the silent-overwrite semantics of a
  repeated identifier. 🟢
- Walk a `ConstructionRootNode` / `ConstructionStepNode` tree depth-first,
  threading a monotonically growing `kwargs` registry and an ordered, copied
  `input_shapes` dict. 🟢
- Isolate top-level branches from each other's `input_shapes`. 🟢
- Load a sub-tree from a file (`JSONStepNode`) and adopt its creator and
  successors. 🟢
- Define the **authoring contract** for new Creators: constructor shape,
  docstring conventions, private-field rule, subpackage registration. 🟢

**Explicitly NOT this use case's responsibility:** the `$TYPE` serialisation
that stores and reloads a tree (→
[`../json-polymorphic-roundtrip/`](../json-polymorphic-roundtrip/requirements.md)),
the topology and coordinate classes the Creators consume (→
[`../wingconfiguration-coordinate-system/`](../wingconfiguration-coordinate-system/requirements.md)),
the individual Creators' geometry algorithms (each Creator is its own body of
CadQuery code, out of scope here), plan CRUD and execution orchestration (→
[`construction-plans`](../../construction-plans/requirements.md)), and the
process pool that isolates a run (→
[`cad-generation`](../../cad-generation/requirements.md)).

## Business Rules

> IDs are inherited verbatim from [`../requirements.md`](../requirements.md).

- **BR-CT3 — `create_shape` is a template method; `_create_shape` is the only
  subclass hook.** 🟢 `create_shape(input_shapes=None, **kwargs)`
  (`AbstractShapeCreator.py:49-61`) resolves upstream shapes, adjusts the log
  level, calls the abstract hook, restores the level, returns the result. No
  Creator in the codebase overrides `create_shape`.
- **BR-CT4 — Positional shape slots are filled most-significant-LAST.** 🟢
  `return_needed_shapes` (l.79-95):

  ```
  len_input = 0 if input_shapes is None else len(input_shapes)
  if sum(x is None for x in shapes_needed) > len_input:
      raise KeyError(f'{identifier}: there are less input_shapes than shapes_needed.')

  if input_shapes is not None:
      enum = input_shapes.keys().__reversed__()
      shapes_needed = [k if k is not None else next(enum) for k in shapes_needed]

  shapes = check_if_shapes_are_available(shapes_needed, **kwargs)
  return {key: shapes[key] for key in shapes_needed}
  ```

  Two subtleties: the guard fires **before** any lookup, and the resolved names
  are looked up in **`kwargs`** (the global registry), not in `input_shapes` —
  positional resolution only *names* a shape, it never supplies the value.
  The returned dict preserves the **declared** order, not the input order.
- **BR-CT5 — A missing declared shape raises, naming the step.** 🟢
  `check_if_shapes_are_available` (l.63-77) returns `{}` when `needed_shapes` is
  `None`; otherwise it raises
  `KeyError(f"shapes are missing in step '{identifier}': {missing}")`.
  🟡 `missing` is assembled through a `set` comprehension, so the order of the
  names in the message is not deterministic.
- **BR-CT6 — A step mutates the ROOT logger level process-wide.** 🟢

  ```
  actual = logging.getLogger().getEffectiveLevel()
  if self.loglevel < actual:
      logging.getLogger().setLevel(self.loglevel)
  result = self._create_shape(...)
  logging.getLogger().setLevel(actual)          # l.60 — NOT in a finally
  ```

  🟡 Three consequences: an exception inside `_create_shape` leaves the level
  lowered for the rest of the process; the restore writes an **explicit** level
  where none may have been set before; and because it is the root logger, two
  concurrent executions in one process interleave.
- **BR-CT7 — The identifier is the output key, and a collision overwrites
  silently.** 🟢 The `identifier` docstring (l.20-27) states it: *"identifier as
  name of this shape. If used several times the shape will be overwritten in
  future steps."* It also warns that the backing attribute must stay public or
  it will not be de/serialised. Conventions (l.43-46): `<identifier>`,
  `<identifier>.<known_name>`, `<identifier>[i]`.
- **BR-CT8 — The base-class `loglevel` default is `FATAL`, the authoring
  convention is `INFO`.** 🟢 `AbstractShapeCreator.__init__` defaults to
  `logging.FATAL` (50); `_creator_template.py:95` uses `logging.INFO` (20) and
  documents the divergence explicitly (l.26).
- **BR-CT9 — A new Creator must be re-exported from its subpackage
  `__init__.py`.** 🟢 Step 5 of the authoring recipe (`_creator_template.py:18`).
  The mechanism belongs to
  [`../json-polymorphic-roundtrip/`](../json-polymorphic-roundtrip/requirements.md)
  (BR-CT15) but the obligation lands on the Creator author.
- **BR-CT10 — A `ConstructionStepNode` never declares its own shape
  requirements.** 🟢 `super().__init__(f"{creator.identifier}",
  shapes_of_interest_keys=None)` (`ConstructionStepNode.py:24`) — so the node's
  own `create_shape` skips resolution entirely and delegates to the wrapped
  Creator. The node's identifier **is** its creator's identifier.
  `ConstructionRootNode`'s is `f"{creator_id}.root"`.
- **BR-CT11 — Traversal threads a growing registry and never mutates the
  caller's dict.** 🟢 (`ConstructionStepNode.py:48-76`)

  ```
  output_shapes = self.creator.create_shape(input_shapes=input_shapes, **kwargs)

  _input_shapes = {} if input_shapes is None else input_shapes.copy()
  for key in output_shapes:
      _input_shapes.pop(key, None)        # remove first …
  _input_shapes.update(output_shapes)     # … so update() re-appends at the END

  kwargs.update(output_shapes)
  for succ in self.successors.values():
      kwargs.update(succ.create_shape(_input_shapes, **kwargs))
  return kwargs
  ```

  The pop-then-update dance exists **only** to guarantee the ordering BR-CT4
  consumes. The copy exists so a child cannot mutate what its siblings see —
  the inline comment says so: *"otherwise we will give a reverence down, which
  will be changed"*.
- **BR-CT12 — The root isolates top-level branches.** 🟢
  `ConstructionRootNode._create_shape` (l.56-57) hands **every** top-level
  successor `input_shapes={}`; only `kwargs` carries the accumulated registry.
  Positional resolution therefore works *within* a branch and **never across**
  top-level branches; named references work everywhere.
- **BR-CT13 — `JSONStepNode` decodes eagerly at construction time.** 🟢
  It opens `json_file_path`, decodes with `GeneralJSONDecoder(**kwargs)`, pops
  `successors` and `creator` from `kwargs`, and adopts the decoded node's
  `creator` and `successors`. `json_file_path` is public (serialised);
  `_to_be_injected` is private (not). All runtime config must be available when
  the node is **built**, not when it is executed.
- **BR-CT31 — Dead code in this slice that a re-implementation must not
  reproduce.** 🟢 **The hinge-type literal keeps all five values; `round_inside`/`round_outside` are declared-but-unimplemented, and the implementation follows** (`Q-CT-5`, maintainer-answered). Measured: no stored row uses either, so there is no harm to a beta user. The genuinely dead items (`AbstractConstructionStep.construct`, `create_XYZ_ted_sketch`, the unimported `scaleXyz` plugin) are recorded for removal under `P-DEAD-0`, but **stated in the spec rather than executed**, because they sit inside the ADR 0002 freeze. `AbstractConstructionStep.construct` (11 l.) is abstract with
  **no implementers** — an abandoned alternative to the Creator contract.
  `ConstructionRootNode._output_shapes` is assigned `None` and never written.
  `create_XYZ_ted_sketch` (`creator/wing/ted_sketch_creators.py:22`) is defined
  but absent from the `ted_sketch_creators` dispatch dict
  (`{"middle","top","top_simple"}`, keyed by `TrailingEdgeDevice.hinge_type`,
  consumed by `VaseModeWingCreator:662`).

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-CX-01 | Provide `AbstractShapeCreator` with `create_shape` as a template method and `_create_shape` as the only abstract hook | Must | A subclass implementing only `_create_shape` is constructible and executable |
| RF-CX-02 | Expose `identifier` (= `creator_id`) as a public, serialisable property | Must | `creator_id` survives a JSON round-trip; `_shapes_of_interest_keys` does not |
| RF-CX-03 | Skip shape resolution entirely when `shapes_of_interest_keys is None` | Must | `_create_shape` receives `shapes_of_interest = None`; no `KeyError` is possible |
| RF-CX-04 | Return `{}` for an empty declared list | Must | A config-driven Creator with `[]` receives an empty dict, not `None` |
| RF-CX-05 | Resolve declared names from the global `kwargs` registry, preserving declared order | Must | `["b","a"]` yields a dict ordered `b`, `a` regardless of registry order |
| RF-CX-06 | Resolve `None` slots from `input_shapes`, most significant last | Must | `[None]` against `{a:…, b:…}` resolves `b` |
| RF-CX-07 | Raise `KeyError` naming the step when there are more `None` slots than input shapes, before any lookup | Must | `[None, None]` with one input raises, and no registry access occurs |
| RF-CX-08 | Raise `KeyError` naming the step and the missing keys when a declared shape is absent | Must | The message contains the identifier and every missing key |
| RF-CX-09 | Lower the root logger to `loglevel` when it is below the effective level, and restore afterwards | Should | Records at `loglevel` are emitted inside `_create_shape`; the previous level is restored |
| RF-CX-10 | Follow the output-key convention for single, named and indexed outputs | Must | Two named outputs produce exactly two dotted keys |
| RF-CX-11 | Overwrite silently on identifier collision | Must | Two steps sharing an identifier leave only the later shape in the registry, without error |
| RF-CX-12 | Make both node classes `MutableMapping` over `successors` | Should | `len(node)`, `node["x"]`, `iter(node)` and `del node["x"]` all operate on `successors` |
| RF-CX-13 | Give a `ConstructionStepNode` its creator's identifier and no declared shapes | Must | `node.identifier == node.creator.identifier`; the node never calls `return_needed_shapes` |
| RF-CX-14 | Give a `ConstructionRootNode` the identifier `f"{creator_id}.root"` | Must | A root built with `"eHawk-wing.root"` has identifier `"eHawk-wing.root.root"` |
| RF-CX-15 | Execute a tree depth-first in `successors` insertion order, returning every shape produced | Must | The root's return value contains the outputs of every step in every branch |
| RF-CX-16 | Order `input_shapes` so the newest keys are last, without mutating the caller's dict | Must | A re-created key appears once and last; the caller's dict is unchanged |
| RF-CX-17 | Hand every top-level successor an empty `input_shapes` | Must | A positional slot in the second top-level branch raises even after the first produced shapes |
| RF-CX-18 | Substitute `{}` for a `None` `input_shapes` before copying | Must | The first step of a branch executes without a `TypeError` |
| RF-CX-19 | Append a successor keyed by its creator's identifier | Should | `parent.append(child)` makes `parent[child.creator.identifier]` the child |
| RF-CX-20 | Load a sub-tree from a file and adopt its creator and successors | Should | A `JSONStepNode` behaves identically to the sub-tree written inline |
| RF-CX-21 | Document the authoring contract in an executable template | Should | A Creator copied from `_creator_template.py` appears in the catalogue with description and tooltips |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Correctness | Registry ordering is an explicit, maintained invariant rather than an accident of dict insertion | `ConstructionStepNode.py:64-71` + the inline comment | 🟢 |
| Correctness | Resolution failures raise before any geometry is built, so a misconfigured plan fails fast | `AbstractShapeCreator.py:75-76, 88-89` | 🟢 |
| Correctness | A step cannot corrupt its siblings' view of the shape stream | `ConstructionStepNode.py:62` (`input_shapes.copy()`) | 🟢 |
| Diagnosability | Both `KeyError` messages name the offending step, which is the only locator a plan author has | `AbstractShapeCreator.py:76, 89` | 🟢 |
| Diagnosability | Log verbosity is controllable per step and travels with the stored plan | `AbstractShapeCreator.py:53-60`; `loglevel` in the `$TYPE` envelope | 🟢 |
| Simplicity | A flat string-keyed registry, no dependency graph, no scheduler — the plan author states the order | `ConstructionStepNode.py:74-75` | 🟢 |
| Concurrency | 🟡 Not thread-safe: the root logger level is process-global for the duration of every step | `AbstractShapeCreator.py:53-60` | 🟡 |
| Robustness | 🟡 The log-level restore is not exception-safe, so a failing step leaves the process noisier than it found it | `AbstractShapeCreator.py:57-61` | 🟡 |

## Acceptance Criteria

```gherkin
Feature: Resolving a step's upstream shapes

  Scenario: A declared shape is delivered from the registry
    Given a registry containing a shape under "wing.loft"
    And a creator whose shapes_of_interest_keys is ["wing.loft"]
    When create_shape is called
    Then _create_shape receives shapes_of_interest containing exactly "wing.loft"

  Scenario: Declared order is preserved regardless of registry order
    Given a registry containing "a" and "b" in that order
    And a creator whose shapes_of_interest_keys is ["b", "a"]
    When create_shape is called
    Then the delivered dict is ordered "b" then "a"

  Scenario: A missing declared shape is rejected by name
    Given a registry that does not contain "wing.loft"
    And a creator whose shapes_of_interest_keys is ["wing.loft"]
    When create_shape is called
    Then a KeyError is raised
    And the message contains the creator's identifier
    And the message contains "wing.loft"

  Scenario: A positional slot takes the most recent input shape
    Given input_shapes ordered as "first" then "second"
    And a creator whose shapes_of_interest_keys is [None]
    When create_shape is called
    Then the creator receives "second"

  Scenario: Too few input shapes is rejected before any lookup
    Given input_shapes containing one shape
    And a creator whose shapes_of_interest_keys is [None, None]
    When create_shape is called
    Then a KeyError is raised
    And the message mentions that there are less input_shapes than shapes_needed
    And no lookup against the registry has occurred

  Scenario: A self-contained creator receives an empty dict
    Given a creator whose shapes_of_interest_keys is []
    When create_shape is called
    Then _create_shape receives an empty shapes_of_interest dict

  Scenario: A creator with no declared keys skips resolution
    Given a creator whose shapes_of_interest_keys is None
    And an empty registry
    When create_shape is called
    Then _create_shape receives shapes_of_interest of None
    And no KeyError is raised

Feature: Log-level handling

  Scenario: A step temporarily lowers the root logger
    Given the root logger is at WARNING
    And a creator whose loglevel is DEBUG
    When create_shape is called
    Then records emitted inside _create_shape at DEBUG are captured
    And the root logger is back at WARNING afterwards

  Scenario: A raising step leaves the level lowered
    Given the root logger is at WARNING
    And a creator whose loglevel is DEBUG and whose _create_shape raises
    When create_shape is called
    Then the exception propagates
    And the root logger is still at DEBUG
    # Documented legacy behaviour — a re-implementation must use try/finally

Feature: Tree traversal

  Scenario: The newest shape is last in the child's input_shapes
    Given input_shapes already containing "earlier"
    And a step whose creator outputs "step.out"
    When the step executes and calls its successor
    Then the successor's input_shapes ends with "step.out"

  Scenario: A re-created key is moved to the end rather than duplicated
    Given input_shapes containing "shape"
    And a step whose creator also outputs "shape"
    When the step executes
    Then the successor's input_shapes contains "shape" exactly once
    And "shape" is the last key

  Scenario: The caller's dict is never mutated
    Given input_shapes containing "earlier"
    When a step executes and produces new shapes
    Then the caller's original input_shapes dict is unchanged

  Scenario: Positional resolution does not cross top-level branches
    Given a root with two top-level successors
    And the first successor produces a shape
    When the second successor executes with a positional slot
    Then its input_shapes is empty
    And a KeyError is raised

  Scenario: A named reference does cross top-level branches
    Given a root with two top-level successors
    And the first successor produces "first.out"
    When the second successor declares ["first.out"]
    Then the shape is delivered from the registry

  Scenario: The root returns every shape produced
    Given a tree with two branches of two steps each
    When the root executes
    Then the returned registry contains the output keys of all four steps

  Scenario: A colliding identifier overwrites silently
    Given two steps that both output the key "part"
    When the tree executes
    Then the registry holds the later step's shape
    And no error is raised

Feature: Sub-tree loading

  Scenario: A JSONStepNode adopts the file's creator and successors
    Given a file containing a serialised construction step with successors
    When a JSONStepNode is built with that path and the required runtime config
    Then its creator and successors match the file's
    And executing it produces the same shapes as the inline equivalent

  Scenario: Missing runtime config fails at construction, not execution
    Given a plan file whose creators require wing_config
    When a JSONStepNode is built without wing_config
    Then the failure occurs while building the node
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| The Creator contract (RF-CX-01…RF-CX-05) | Must | Every one of the 29 Creators, both node types and the serialisation layer are written against it |
| Positional resolution and its guards (RF-CX-06…RF-CX-08) | Must | The authored blueprints rely on `None` slots; a wrong resolution silently builds the wrong solid |
| Tree traversal and the ordering invariant (RF-CX-15, RF-CX-16) | Must | The only reason positional resolution is deterministic |
| Branch isolation (RF-CX-17) | Must | Load-bearing: without it, a second branch would resolve slots against an unrelated branch's output |
| Output-key convention (RF-CX-10) | Must | The registry is keyed entirely by these strings; every cross-step reference depends on the format |
| `None` `input_shapes` substitution (RF-CX-18) | Must | Every branch's first step takes this path |
| `MutableMapping` protocol (RF-CX-12) | Should | Used by `construction-plans`' step counting and export-path rewriting, but a plain attribute would work |
| Log-level handling (RF-CX-09) | Should | Diagnostics only; plans in the wild set it per node so it must be honoured |
| `append` keyed by creator identifier (RF-CX-19) | Should | A programmatic convenience; the stored form is the `successors` dict |
| `JSONStepNode` (RF-CX-20) | Should | Used by the authored `test/` plans; `app/` inlines its trees instead |
| The authoring template (RF-CX-21) | Should | Not executable behaviour, but the Creator Catalog's tooltips and descriptions depend on the docstring conventions |
| Silent overwrite on collision (RF-CX-11) | Could | Documented legacy behaviour; a re-implementation may reasonably choose to raise instead (see 🔴 below) |
| `AbstractConstructionStep` | Won't | Abstract with no implementers — an abandoned design |
| `ConstructionRootNode._output_shapes` | Won't | Assigned `None`, never written |
| `create_XYZ_ted_sketch` | Won't | Defined but absent from the dispatch dict |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `cad_designer/airplane/AbstractShapeCreator.py` (95 l.) | `__init__`, `identifier`, `shapes_of_interest_keys`, `_create_shape`, `create_shape`, `check_if_shapes_are_available`, `return_needed_shapes` | 🟢 |
| `cad_designer/airplane/ConstructionStepNode.py` (77 l.) | `__init__`, `MutableMapping` protocol, `append`, `_create_shape` | 🟢 |
| `cad_designer/airplane/ConstructionRootNode.py` (59 l.) | `__init__`, `MutableMapping` protocol, `append`, `_create_shape`, `_output_shapes` | 🟢 |
| `cad_designer/airplane/JSONStepNode.py` (24 l.) | eager decode, `_to_be_injected`, kwarg popping | 🟢 |
| `cad_designer/airplane/AbstractConstructionStep.py` (11 l.) | `construct` | 🟢 (dead) |
| `cad_designer/airplane/creator/_creator_template.py` (170 l.) | the authoring contract: docstring conventions, `suggested_creator_id`, private config, `shapes_of_interest_keys` variants, output-dict variations | 🟢 |
| `cad_designer/airplane/creator/*/__init__.py` | the five re-export lists (29 Creators) | 🟢 |
| `cad_designer/airplane/creator/wing/ted_sketch_creators.py` | `ted_sketch_creators` dispatch; `create_XYZ_ted_sketch` (dead) | 🟢 |
