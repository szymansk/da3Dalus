# creator-execution-model — Technical Design

> Use-case design, nested under the module
> [`cad-designer-topology`](../design.md).
> Focuses on HOW this use case is built, derived from the legacy code.
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Library API in full: [`../contracts.md`](../contracts.md) §1–§2.
> Sibling slices: [`../wingconfiguration-coordinate-system/`](../wingconfiguration-coordinate-system/design.md),
> [`../json-polymorphic-roundtrip/`](../json-polymorphic-roundtrip/design.md).
>
> ⚠ Frozen layer (ADR 0002).

## Interface

### `AbstractShapeCreator` — `cad_designer/airplane/AbstractShapeCreator.py` (95 l.) 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `__init__` | `(creator_id: CreatorId, shapes_of_interest_keys: list[ShapeId] \| None, loglevel: int = logging.FATAL)` | — | assigns `self.loglevel`, `self._shapes_of_interest_keys`, `self.creator_id` in that order (l.16-18) |
| `identifier` | property | `CreatorId` | `return self.creator_id` (l.27); docstring warns the backing field must stay public |
| `shapes_of_interest_keys` | property | `list[ShapeId]` | `return self._shapes_of_interest_keys` — may be `None` |
| `_create_shape` | `(shapes_of_interest: dict \| None, input_shapes: dict, **kwargs)` | `dict[ShapeId, Workplane]` | `@abc.abstractmethod` (l.33-47) |
| `create_shape` | `(input_shapes: dict = None, **kwargs)` | `dict[ShapeId, Workplane]` | template method (l.49-61) |
| `check_if_shapes_are_available` | `(needed_shapes: list[ShapeId], **kwargs)` | `dict` | raises `KeyError` naming step + missing keys (l.63-77) |
| `return_needed_shapes` | `(shapes_needed: list[ShapeId], input_shapes: dict, **kwargs)` | `dict` | positional fill + availability check (l.79-95) |

The class is `abc.ABCMeta`-based, so instantiating a subclass that has not
implemented `_create_shape` raises `TypeError` at construction. 🟢

### The construction tree 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `ConstructionStepNode.__init__` | `(creator: AbstractShapeCreator, successors: OrderedDict[CreatorId, T] = None, **kwargs)` | — | `successors` defaults to a fresh `OrderedDict`; calls `super().__init__(f"{creator.identifier}", shapes_of_interest_keys=None)` (l.22-24) |
| `ConstructionStepNode.append` | `(value)` | `None` | `self.update({value.creator.identifier: value})` (l.41-46) |
| `ConstructionStepNode._create_shape` | `(shapes_of_interest, input_shapes, **kwargs)` | `dict` | the traversal core (l.48-76) |
| `ConstructionRootNode.__init__` | `(creator_id: CreatorId, successors: OrderedDict = None)` | — | sets `self._output_shapes = None` 🟡 vestigial; identifier `f"{creator_id}.root"` (l.18-24) |
| `ConstructionRootNode._create_shape` | same | `dict` | hands each successor `input_shapes={}` (l.48-58) |
| `JSONStepNode.__init__` | `(json_file_path: str, **kwargs)` | — | eager decode + adopt (l.5-24) |
| `AbstractConstructionStep.construct` | `(input_shapes: list[Workplane], **kwargs)` | `list[Workplane]` | 🔴 abstract, **no implementers** |

Both node classes subclass `AbstractShapeCreator` **and** `MutableMapping`,
implementing `__getitem__`, `__setitem__`, `__delitem__`, `__len__` and
`__iter__` over `successors`. `MutableMapping` supplies `update`, `keys`,
`values`, `items`, `pop` and `__contains__` for free — which is what makes
`append`'s `self.update({...})` work. 🟢

### The authoring contract — `creator/_creator_template.py` (170 l.) 🟢

| Element | Rule |
|---|---|
| File placement | one of `cad_operations/`, `wing/`, `fuselage/`, `export_import/`, `components/` |
| `suggested_creator_id` | class attribute; may contain `{param}` placeholders resolved at decode time |
| Class docstring, first line | the Creator Gallery description and the parameter-form header |
| Docstring `Attributes:` block | lines `name (type): Description text.` become per-parameter tooltips |
| Docstring `Returns:` block | keys like `{id}` / `{id}.cape` become the declared outputs |
| Domain parameters | stored as **public** attributes **before** `super().__init__` |
| Runtime-injected config | stored as `self._private` so the encoder skips it |
| `shapes_of_interest_keys` | `[self.input_shape]` single · `[self.a, self.b]` multiple · `[self.minuend] + self.subtrahends` fixed+variable · `[]` self-contained |
| `loglevel` | default `logging.INFO` in new Creators (the base class defaults to `FATAL`) |
| Registration | must be re-exported from the subpackage `__init__.py` |
| `_create_shape` body | log → take shapes from `shapes_of_interest` (not `input_shapes`) → operate → `result.display(name=self.identifier, severity=logging.DEBUG)` → return `{self.identifier: result}` |

The template explicitly tells authors to use `shapes_of_interest` as the primary
input and **not** to reach into `input_shapes` directly (l.121-124) — the
positional protocol exists precisely so they do not have to. 🟢

## Main Flow

### F1 — One Creator executes 🟢

```
create_shape(input_shapes, **kwargs):                     # l.49-61

  1. shapes_of_interest = (
         return_needed_shapes(self.shapes_of_interest_keys, input_shapes, **kwargs)
         if self.shapes_of_interest_keys is not None
         else None
     )

  2. actual_loglevel = logging.getLogger().getEffectiveLevel()
     if self.loglevel < actual_loglevel:
         logging.getLogger().setLevel(level=self.loglevel)

  3. result = self._create_shape(shapes_of_interest, input_shapes, **kwargs)

  4. logging.getLogger().setLevel(level=actual_loglevel)   # unconditional, NOT in finally
  5. return result
```

Step 2 lowers only — a Creator cannot make the log *quieter* than the ambient
level. Step 4 restores unconditionally on the success path, and writes an
explicit level even if the root previously had none set (`NOTSET` inherits, an
explicit level does not). 🟡

### F2 — Positional and named resolution 🟢

```
return_needed_shapes(shapes_needed, input_shapes, **kwargs):     # l.79-95

  len_input_shapes = 0 if input_shapes is None else len(input_shapes)

  if sum(x is None for x in shapes_needed) > len_input_shapes:
      raise KeyError(f'{self.identifier}: there are less input_shapes than shapes_needed.')

  if input_shapes is not None:
      enum = input_shapes.keys().__reversed__()       # ← most significant LAST
      shapes_needed = [k if k is not None else next(enum) for k in shapes_needed]

  shapes = self.check_if_shapes_are_available(shapes_needed, **kwargs)
  return {key: shapes[key] for key in shapes_needed}  # ← declared order preserved
```

```
check_if_shapes_are_available(needed_shapes, **kwargs):          # l.63-77

  shapes = {}
  if needed_shapes is not None:
      shapes  = {k: kwargs[k] for k in needed_shapes if k in kwargs}
      missing = {(k if k not in kwargs else None) for k in needed_shapes}   # a SET
      missing = [i for i in missing if i is not None]
      if missing:
          raise KeyError(f"shapes are missing in step '{self.identifier}': {missing}")
  return shapes
```

Three design consequences worth pinning:

- **Values always come from `kwargs`.** `input_shapes` supplies only the *names*
  for positional slots. A shape present in `input_shapes` but absent from
  `kwargs` would still raise — impossible in practice, because
  `ConstructionStepNode` writes to both.
- **Left-to-right consumption.** `next(enum)` walks the reversed key iterator, so
  `[None, None]` against `{a, b, c}` resolves to `c` then `b`. The list
  comprehension evaluates left to right, which fixes the pairing.
- **Order is declared, not resolved.** The final dict comprehension iterates
  `shapes_needed`, so the delivered order matches the Creator's declaration.
  🟡 If the same key appears twice in `shapes_needed`, the dict silently
  collapses it to one entry.

### F3 — Walking the tree 🟢

```
root.create_shape()                                  # shapes_of_interest_keys is None
└─ ConstructionRootNode._create_shape(None, None, **kwargs)      # l.48-58
      for key in self.successors:
          kwargs.update(self.successors[key].create_shape(input_shapes={}, **kwargs))
      return kwargs

ConstructionStepNode._create_shape(_, input_shapes, **kwargs)    # l.48-76
      output_shapes = self.creator.create_shape(input_shapes=input_shapes, **kwargs)

      _input_shapes = {} if input_shapes is None else input_shapes.copy()

      for key in output_shapes:                      # remove …
          try:    del _input_shapes[key]
          except KeyError: pass
      _input_shapes.update(output_shapes.copy())     # … then re-append at the END

      kwargs.update(output_shapes.copy())
      for key in self.successors:
          kwargs.update(self.successors[key].create_shape(_input_shapes, **kwargs))
      return kwargs
```

The two dicts have deliberately different lifetimes:

| | `kwargs` (registry) | `_input_shapes` (stream) |
|---|---|---|
| Scope | the whole run | one parent→child edge |
| Mutation | shared, accumulates monotonically | copied per step |
| Purpose | named lookups from anywhere in the branch chain | positional slot resolution |
| Root behaviour | threaded into every branch | reset to `{}` per top-level branch |

🟡 Note `kwargs.update(...)` on the recursion line: because each successor
*returns* the whole registry, the parent re-absorbs it, so shapes produced deep
in a branch are visible to that branch's later siblings.

### F4 — Sub-tree loading 🟢

```
JSONStepNode(json_file_path, **kwargs):                          # l.5-24

  self.json_file_path = json_file_path        # PUBLIC  → serialised
  self._to_be_injected = kwargs               # PRIVATE → not serialised

  creator = json.load(open(json_file_path), cls=GeneralJSONDecoder, **self._to_be_injected)

  kwargs.pop("successors", None)
  kwargs.pop("creator", None)
  super().__init__(creator=creator.creator, successors=creator.successors, **kwargs)
```

The decoded object is a `ConstructionStepNode`; the `JSONStepNode` takes over its
`creator` and `successors` rather than nesting it. The file handle is closed
explicitly (l.19), not via a context manager. 🟡 An exception during decode would
leak it.

## Alternative Flows

- **`shapes_of_interest_keys is None`** — resolution skipped; `_create_shape`
  receives `None`. Both node classes always take this path (BR-CT10). 🟢
- **`shapes_of_interest_keys == []`** — `return_needed_shapes` runs, finds no
  `None` slots (so the guard passes trivially), and returns `{}`. This is the
  documented shape for config-driven Creators. 🟢
- **`input_shapes is None`** — `return_needed_shapes` treats the length as `0`,
  so *any* `None` slot raises; `ConstructionStepNode._create_shape` substitutes
  `{}` before copying (l.59-62). 🟢
- **Too few input shapes** — `KeyError` from the guard, before any registry
  access. 🟢
- **Missing declared key** — `KeyError` from `check_if_shapes_are_available`,
  naming the step. 🟡 The names' order in the message is not stable (set-based).
- **Duplicate key in `shapes_needed`** — the returned dict collapses it to one
  entry; no error. 🟡
- **Identifier collision between steps** — the later `kwargs.update` overwrites
  the earlier shape silently; nothing detects it. 🟢
- **`_create_shape` raises** — the exception propagates through `create_shape`
  and the whole tree walk unwinds; the root logger level is **not** restored. 🟡
- **A Creator returns a non-dict** — `for key in output_shapes` would iterate
  something unexpected; nothing validates the return type. 🟡 INFERRED risk; no
  guard was found.

## Dependencies

- **CadQuery** — `Workplane` appears in the abstract signature itself, so the
  contract cannot be imported without it.
- **`cad_designer.airplane.types`** — `CreatorId`, `ShapeId`
  (→ [`../wingconfiguration-coordinate-system/`](../wingconfiguration-coordinate-system/design.md)
  documents the type vocabulary).
- **`GeneralJSONDecoder`** — only `JSONStepNode` depends on it, and only at
  construction time (→
  [`../json-polymorphic-roundtrip/`](../json-polymorphic-roundtrip/design.md)).
- **stdlib `logging`, `abc`, `collections.OrderedDict`, `typing.MutableMapping`.**
- **Consumers:** `construction-plans` (decodes a tree and calls
  `root.create_shape()`; walks `successors` for step counting and export-path
  rewriting), `cad-generation` (calls `WingLoftCreator._create_shape` **directly**
  in the tessellation worker, bypassing the template method — 🟡 off-contract but
  harmless there, since no upstream shapes are involved).

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| A template method with one abstract hook, rather than a free-form interface | `AbstractShapeCreator.py:49-61` vs. the unused `AbstractConstructionStep` | 🟢 |
| Shape identity is a **string key in a flat registry**, not an object reference | `identifier` docstring l.20-27; `kwargs` threading | 🟢 |
| Positional slots resolve from an **ordered dict**, not by index | `return_needed_shapes` l.90-92 + the pop/update dance l.64-71 | 🟢 |
| The ordering invariant is maintained explicitly at every step, not assumed | `ConstructionStepNode.py:64-71` | 🟢 |
| Children get a **copy** so siblings are isolated; the registry is deliberately shared | `ConstructionStepNode.py:62` + inline comment | 🟢 |
| Top-level branches are isolated from each other's shape stream | `ConstructionRootNode.py:56-57` | 🟢 |
| A node delegates all resolution to its creator, declaring nothing itself | `ConstructionStepNode.py:24` | 🟢 |
| Tree nodes are `MutableMapping`s, so a plan is navigable as a plain dict | both node classes | 🟢 |
| Verbosity is per-step and travels with the plan, rather than being global config | `loglevel` on every node + `AbstractShapeCreator.py:53-60` | 🟢 |
| Identifier collisions are documented rather than prevented | `identifier` docstring l.25 | 🟢 |
| The authoring contract lives in an executable template, not in prose docs | `_creator_template.py` | 🟢 |
| `JSONStepNode` decodes eagerly, so config must exist at build time | `JSONStepNode.py:15-18` | 🟢 |

## Internal State

- **Per run, shared** — the `kwargs` shape registry: `dict[ShapeId, Workplane]`,
  grows monotonically for the life of one `root.create_shape()` call, discarded
  afterwards. It is passed as `**kwargs`, so every level receives a *new* dict
  object that is then `update`d — the accumulation works because each callee
  returns its registry and the caller merges it back.
- **Per edge, copied** — `_input_shapes`: the ordered shape stream handed from a
  step to its successors. Never shared between siblings.
- **Per node** — `successors` (`OrderedDict`), `creator`, `creator_id`,
  `loglevel`, `_shapes_of_interest_keys`; `JSONStepNode` adds `json_file_path`
  and `_to_be_injected`; `ConstructionRootNode._output_shapes` is initialised to
  `None` and never assigned again. 🟡 Vestigial.
- **Process-global, mutated** 🟡 — the **root** logger level, for the duration of
  every step.

There is no persistence, no caching and no cross-run state in this slice. 🟢

## Observability

- **Per-step level control.** `loglevel` is serialised into the plan, so a plan
  author can turn one step verbose without touching code. The authored wing
  blueprint uses `50` on the structural nodes, `10` on `WingLoftCreator` and `20`
  on the exporter. 🟢
- **Creator-authored progress line.** The template prescribes
  `logging.info(f"processing '{keys}' --> '{self.identifier}'")` as the first
  statement of `_create_shape` (l.135-139), which makes the log a readable trace
  of the shape graph. 🟢
- **Visual dumps.** `result.display(name=self.identifier, severity=logging.DEBUG)`
  (l.149) — inert unless `DISPLAY_CONSTRUCTION_STEP` is set; when set, this is
  the event source `construction-plans` streams over SSE.
  See [`../wingconfiguration-coordinate-system/design.md`](../wingconfiguration-coordinate-system/design.md)
  §CadQuery extensions for the gate. 🟢
- **Failure diagnostics.** Both `KeyError` messages embed `self.identifier`,
  which is the only locator a plan author has — there is no step index, no path
  and no stack of enclosing nodes. 🟡 In a deep tree with duplicated creator ids
  (permitted, BR-CT7) the message is ambiguous.
- **No metrics, no timing, no step events.** Duration and success accounting
  belong to `construction-plans`. 🟢

## Risks and Gaps

- 🔴 **`AbstractConstructionStep` has no implementers.** An abandoned parallel
  design (`construct(list[Workplane]) -> list[Workplane]`) that survives as an
  importable abstract class, inviting a future author to implement the wrong
  contract.
- 🔴 **`create_XYZ_ted_sketch` is unreachable.** Defined in
  `ted_sketch_creators.py:22` but absent from the dispatch dict, so a
  `TrailingEdgeDevice` requesting that hinge style would `KeyError` rather than
  fall back.
- 🟡 Must emit a `DesignWarning` rather than failing silently (`P-WARN-0`). Previously identifier collisions were silent. In a large tree, an accidentally
  duplicated `creator_id` produces a missing-shape symptom several steps later,
  with no diagnostic pointing at the collision.
- 🟡 **The log-level restore is not exception-safe** (l.57-61), so a failing step
  leaves the root logger lowered for the remainder of the process.
- 🟡 **Root-logger mutation is process-global**, so concurrent executions in one
  process interleave verbosity — the same tension ADR 0005 records between
  `cad-generation`'s process pool and `construction-plans`' in-process execution.
- 🟡 **The missing-keys message has non-deterministic ordering** because
  `missing` is built through a `set` comprehension.
- 🟡 **A duplicated entry in `shapes_needed` collapses silently** in the final
  dict comprehension.
- 🟡 **Nothing validates a Creator's return type.** A Creator returning a list or
  `None` would fail obscurely inside the traversal rather than at its own
  boundary.
- 🟡 **`JSONStepNode` closes its file handle manually**, so a decode failure
  leaks it; and because the decode is eager, a plan referencing a missing file
  fails while the tree is being *built*, which reads as a decode error rather
  than a missing-asset error.
- 🟡 **`cad-generation` calls `WingLoftCreator._create_shape` directly**,
  bypassing `create_shape`. Harmless today (no upstream shapes, no log-level
  expectation) but it means the private hook is de-facto public for at least one
  consumer.
- 🟢 **`ConstructionRootNode._output_shapes` is vestigial** — assigned `None` and
  never written. Documented, not fixed (frozen layer).
