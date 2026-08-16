# creator-execution-model — Implementation Tasks

> Use-case task list, nested under the module
> [`cad-designer-topology`](../tasks.md).
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
>
> ⚠ **Frozen layer (ADR 0002).** These tasks describe **what a re-implementation
> must reproduce**, not edits to make in `cad_designer/`. See
> `### Preservation constraints` for the split between behaviour to carry
> forward and defects to leave behind.

## Prerequisites

- [ ] CadQuery available — `Workplane` appears in the abstract `_create_shape`
      signature, so the contract cannot be imported without it (ADR 0017).
- [ ] `CreatorId` / `ShapeId` type aliases exist
      (→ [`../wingconfiguration-coordinate-system/tasks.md`](../wingconfiguration-coordinate-system/tasks.md) T-WC-01).
- [ ] A decision on the **shape-registry model**: a flat `dict[str, Workplane]`
      threaded through the walk, keyed by creator identifier. Everything in this
      slice follows from it.
- [ ] A decision on **whether concurrent execution in one process is supported**
      — it determines whether the log-level handling can stay global
      (→ [`../tasks.md`](../tasks.md) T-35).

## Tasks

### The Creator base class

- [ ] **T-CX-01 — `AbstractShapeCreator` constructor and properties.**
  `__init__(creator_id: CreatorId, shapes_of_interest_keys: list[ShapeId] | None,
  loglevel: int = logging.FATAL)` assigning `self.loglevel`,
  `self._shapes_of_interest_keys` (**private**) and `self.creator_id`
  (**public**). `identifier` property returns `creator_id`;
  `shapes_of_interest_keys` property returns the private field. Use `ABCMeta` so
  a subclass without `_create_shape` fails at instantiation.
  - Legacy origin: `cad_designer/airplane/AbstractShapeCreator.py:11-31`
  - Definition of done: `creator_id` and `loglevel` survive a JSON round-trip
    while `_shapes_of_interest_keys` does not; instantiating an incomplete
    subclass raises `TypeError`.
  - Confidence: 🟢

- [ ] **T-CX-02 — `create_shape` template method.**
  Resolve shapes only when `shapes_of_interest_keys is not None`; read the
  effective **root** logger level; lower it when `self.loglevel` is below it;
  call `_create_shape(shapes_of_interest, input_shapes, **kwargs)`; restore the
  previous level; return the result.
  - Legacy origin: `AbstractShapeCreator.py:49-61`
  - Definition of done: with the root at `WARNING` and `loglevel = DEBUG`,
    records emitted inside `_create_shape` are captured and the root is back at
    `WARNING` afterwards; a creator with `loglevel = FATAL` never *raises* the
    ambient level.
  - Confidence: 🟢

- [ ] **T-CX-03 — Positional slot resolution (`return_needed_shapes`).**
  Compute `len_input = 0 if input_shapes is None else len(input_shapes)`; raise
  `KeyError(f'{identifier}: there are less input_shapes than shapes_needed.')`
  when `count(None) > len_input`; otherwise replace each `None` from
  `input_shapes.keys().__reversed__()` left to right; look the resolved names up
  via `check_if_shapes_are_available`; return a dict in the **declared** order.
  - Legacy origin: `AbstractShapeCreator.py:79-95`
  - Definition of done: `[None]` against `{"a","b"}` resolves `b`;
    `[None, None]` against `{"a","b","c"}` resolves `c` then `b`;
    `["a", None]` resolves the named key from the registry and the slot from the
    inputs; the guard fires with zero registry accesses.
  - Confidence: 🟢

- [ ] **T-CX-04 — Registry availability check.**
  Return `{}` when `needed_shapes is None`; otherwise collect the present keys
  from `kwargs` and raise
  `KeyError(f"shapes are missing in step '{identifier}': {missing}")` listing
  every absent key.
  - Legacy origin: `AbstractShapeCreator.py:63-77`
  - Definition of done: the message names the step and every missing key; a
    test asserts the *set* of names rather than their order (see T-CX-19).
  - Confidence: 🟢

- [ ] **T-CX-05 — Output-key convention.**
  `<identifier>` for a single shape, `<identifier>.<known_name>` for named
  outputs, `<identifier>[i]` for indexed ones; export-style Creators return
  `shapes_of_interest` unchanged as a pass-through.
  - Legacy origin: `AbstractShapeCreator.py:43-46`;
    `creator/_creator_template.py:129-169`
  - Definition of done: a Creator returning two named shapes produces exactly
    two dotted keys; a pass-through Creator leaves the registry unchanged in
    content.
  - Confidence: 🟢

### The construction tree

- [ ] **T-CX-06 — `ConstructionStepNode` as Creator + `MutableMapping`.**
  `__init__(creator, successors: OrderedDict = None, **kwargs)` defaulting
  `successors` to a fresh `OrderedDict` and calling
  `super().__init__(f"{creator.identifier}", shapes_of_interest_keys=None)`.
  Implement `__getitem__`, `__setitem__`, `__delitem__`, `__len__`, `__iter__`
  over `successors`, plus `append(value)` keyed by `value.creator.identifier`.
  - Legacy origin: `cad_designer/airplane/ConstructionStepNode.py:12-46`
  - Definition of done: `node.identifier == node.creator.identifier`; `len`,
    indexing, iteration and deletion all operate on `successors`;
    `parent.append(child)` makes `parent[child.creator.identifier]` the child.
  - Confidence: 🟢

- [ ] **T-CX-07 — `ConstructionStepNode._create_shape` traversal.**
  Call the creator; build `_input_shapes` as `{}` when `input_shapes is None`
  else a **copy**; delete every key the creator just produced; update with the
  outputs so they land **last**; `kwargs.update(output_shapes)`; recurse into
  every successor with `_input_shapes` and the registry, merging each return
  value back into `kwargs`; return `kwargs`.
  - Legacy origin: `ConstructionStepNode.py:48-76`
  - Definition of done: a re-created key appears exactly once and last in the
    child's `input_shapes`; the caller's dict is provably unmutated; the return
    value contains every shape produced by every descendant.
  - Confidence: 🟢

- [ ] **T-CX-08 — `ConstructionRootNode` and branch isolation.**
  Identifier `f"{creator_id}.root"`; `successors` defaulting to a fresh
  `OrderedDict`; the same `MutableMapping` protocol and `append`; `_create_shape`
  handing **every** top-level successor `input_shapes={}` and threading only
  `kwargs`.
  - Legacy origin: `cad_designer/airplane/ConstructionRootNode.py:18-58`
  - Definition of done: a root built with `"eHawk-wing.root"` has identifier
    `"eHawk-wing.root.root"`; a positional slot in the second top-level branch
    raises `KeyError` even after the first branch produced shapes; a named
    reference across branches resolves.
  - Confidence: 🟢

- [ ] **T-CX-09 — `JSONStepNode` eager sub-tree loading.**
  Store `json_file_path` publicly and the injection payload as
  `_to_be_injected`; decode the file with the plan decoder at construction time;
  pop `successors` and `creator` from `kwargs`; adopt the decoded node's
  `creator` and `successors`.
  - Legacy origin: `cad_designer/airplane/JSONStepNode.py:4-24`
  - Definition of done: the node behaves identically to the sub-tree written
    inline; a test documents that runtime config must be supplied at **build**
    time; the file handle is closed even when the decode raises (see T-CX-22).
  - Confidence: 🟢

### The authoring contract

- [ ] **T-CX-10 — Creator authoring conventions.**
  `suggested_creator_id` class attribute (may contain `{param}` placeholders);
  first docstring line = catalogue description; `Attributes:` block of
  `name (type): text` lines = per-parameter tooltips; `Returns:` block = declared
  output keys; domain parameters stored **publicly before** `super().__init__`;
  runtime-injected config stored as `self._private`; `loglevel` defaulting to
  `logging.INFO`; the four `shapes_of_interest_keys` idioms
  (`[named]`, `[a, b]`, `[fixed] + variable`, `[]`).
  - Legacy origin: `cad_designer/airplane/creator/_creator_template.py:1-111`
  - Definition of done: a Creator written from the template appears in the
    Creator Catalog with a description and per-parameter tooltips (the catalogue
    reflection itself is owned by
    [`construction-plans`](../../construction-plans/tasks.md)).
  - Confidence: 🟢

- [ ] **T-CX-11 — `_create_shape` body conventions.**
  Log `f"processing '{keys}' --> '{self.identifier}'"` first; take inputs from
  `shapes_of_interest`, **not** `input_shapes`; call
  `result.display(name=self.identifier, severity=logging.DEBUG)` before
  returning; return `{self.identifier: result}`.
  - Legacy origin: `_creator_template.py:113-169`
  - Definition of done: the log line makes the shape graph readable end to end;
    a lint or review checklist covers the "don't touch `input_shapes`" rule.
  - Confidence: 🟢

- [ ] **T-CX-12 — The 29-Creator inventory and its five packages.**
  `cad_operations/` (9), `wing/` (3), `fuselage/` (9), `export_import/` (6),
  `components/` (2), each re-exported from its subpackage `__init__.py`, with the
  package root star-importing all five. Full class list in
  [`../design.md`](../design.md) §Creator inventory.
  - Legacy origin: `cad_designer/airplane/creator/__init__.py` and the five
    subpackage `__init__.py` files
  - Definition of done: a star-import exposes every class in the inventory; a
    test asserts the count so a silently unregistered Creator is caught.
  - Confidence: 🟢

- [ ] **T-CX-13 — The `ted_sketch_creators` dispatch.**
  A plain dict `{"middle": …, "top": …, "top_simple": …}` keyed by
  `TrailingEdgeDevice.hinge_type`, consumed by `VaseModeWingCreator`.
  Deliberately **not** a Creator module and intentionally absent from
  `wing/__init__.py`.
  - Legacy origin: `creator/wing/ted_sketch_creators.py:187`;
    `creator/wing/VaseModeWingCreator.py:662`
  - Definition of done: each of the three hinge types resolves to a sketch
    builder; an unknown hinge type produces a clear error rather than a bare
    `KeyError` (see T-CX-21).
  - Confidence: 🟢

### Preservation constraints

> Behaviour to **reproduce**, and defects **not** to carry forward. Nothing here
> authorises editing the legacy files (ADR 0002).

- [ ] **T-CX-14 — REPRODUCE: the ordering invariant, deliberately.**
  The pop-then-update in `_create_shape` is the *only* reason positional
  resolution is deterministic. Implement it with a comment naming the
  dependency, and add a regression test that fails if the pop loop is removed.
  - Legacy origin: `ConstructionStepNode.py:64-71`; `AbstractShapeCreator.py:90-92`
  - Definition of done: deleting the pop loop makes a named test fail with a
    message explaining which shape a positional slot would then resolve to.
  - Confidence: 🟢

- [ ] **T-CX-15 — REPRODUCE: branch isolation at the root.**
  Every top-level successor receives an empty `input_shapes`. This is
  load-bearing, not incidental — without it a second branch's positional slot
  would silently resolve against an unrelated branch's output.
  - Legacy origin: `ConstructionRootNode.py:56-57`
  - Definition of done: the cross-branch positional `KeyError` is asserted as
    **intended** behaviour, with the rationale in the test name.
  - Confidence: 🟢

- [ ] **T-CX-16 — DO NOT REPRODUCE: the non-exception-safe log-level restore.**
  Wrap the `_create_shape` call in `try/finally` so a raising step still restores
  the previous root level.
  - Legacy origin: `AbstractShapeCreator.py:57-61`
  - Definition of done: a `_create_shape` that raises leaves the root logger at
    its original level; a test asserts it.
  - Confidence: 🟢

- [ ] **T-CX-17 — DO NOT REPRODUCE: `AbstractConstructionStep`.**
  An abstract `construct(input_shapes: list[Workplane], **kwargs) ->
  list[Workplane]` with no implementers — an abandoned parallel design that
  invites a future author to implement the wrong contract.
  - Legacy origin: `cad_designer/airplane/AbstractConstructionStep.py:4-11`
  - Definition of done: the class does not exist in the re-implementation, and
    the omission is listed in the migration notes.
  - Confidence: 🟢

- [ ] **T-CX-18 — DO NOT REPRODUCE: dead attributes and unreachable helpers.**
  `ConstructionRootNode._output_shapes` (assigned `None`, never written);
  `create_XYZ_ted_sketch` (defined, absent from the dispatch dict).
  - Legacy origin: `ConstructionRootNode.py:23`;
    `creator/wing/ted_sketch_creators.py:22`
  - Definition of done: neither exists; both are named in the migration notes so
    a reviewer can confirm the omission was intentional.
  - Confidence: 🟢

- [ ] **T-CX-19 — RESOLVE: non-deterministic missing-key message.**
  `missing` is assembled through a `set` comprehension, so the names appear in
  arbitrary order — awkward for both humans and snapshot tests.
  - Legacy origin: `AbstractShapeCreator.py:73-76`
  - Definition of done: the re-implementation preserves the **declared** order of
    the missing keys; a decision is recorded that the change is cosmetic and
    behaviour-preserving.
  - Confidence: 🟡 INFERRED — the fix is obvious, but confirm no consumer parses
    the message.

- [ ] **T-CX-20 — RESOLVE: should an identifier collision raise?**
  Today the later shape silently overwrites the earlier one
  (`AbstractShapeCreator.identifier` docstring l.25). In a large tree the symptom
  surfaces several steps later as a missing or wrong shape.
  - Legacy origin: `AbstractShapeCreator.py:20-27`; `ConstructionStepNode.py:73`
  - Definition of done: a human decides between "keep silent overwrite (some
    plans may rely on re-creating a key)" and "raise on collision"; whichever is
    chosen is covered by a test that states the intent.
  - Confidence: 🟢 — decided (`Q-CT-5`). Note that T-CX-14's pop loop
    explicitly *supports* re-creating a key within a branch, so a blanket raise
    would be a behaviour change.

- [ ] **T-CX-21 — RESOLVE: unvalidated Creator return values and dispatch keys.**
  Nothing checks that `_create_shape` returned a dict, and
  `ted_sketch_creators[hinge_type]` has no guarded fallback.
  - Legacy origin: `ConstructionStepNode.py:57-71`;
    `creator/wing/ted_sketch_creators.py:187`
  - Definition of done: a decision on whether to validate at the Creator
    boundary; if yes, a clear error naming the offending step replaces the
    downstream failure.
  - Confidence: 🟡

- [ ] **T-CX-22 — RESOLVE: `JSONStepNode` file handling and failure mode.**
  The file is opened and closed manually (leaked on a decode failure), and the
  eager decode means a missing file or missing runtime config surfaces while the
  *tree is being built*, which reads as a decode error rather than a missing
  asset.
  - Legacy origin: `JSONStepNode.py:15-19`
  - Definition of done: a context manager is used; a decision is recorded on
    whether decoding should stay eager (it must, if runtime config is to be
    injected once) and the error message distinguishes "file missing" from
    "plan invalid".
  - Confidence: 🟡

## Test Tasks

- [ ] **TT-CX-01 — Happy path:** a two-branch, two-deep tree executes and the
      root returns the output keys of all four steps.
- [ ] **TT-CX-02 — Failure:** a declared shape missing from the registry raises
      `KeyError` naming the step and the key.
- [ ] **TT-CX-03 — Positional matrix:** `[None]`, `[None, None]`, `["a", None]`
      against 0, 1, 2 and 3 input shapes, including the
      "less input_shapes than shapes_needed" raise and the left-to-right pairing
      (`[None, None]` on `{a,b,c}` → `c` then `b`).
- [ ] **TT-CX-04 — Declared order preserved:** `["b","a"]` yields a dict ordered
      `b` then `a` regardless of registry insertion order.
- [ ] **TT-CX-05 — Guard fires before lookup:** with a spy registry, the
      too-few-inputs raise performs zero accesses.
- [ ] **TT-CX-06 — `None` and `[]` declarations:** `None` skips resolution and
      delivers `None`; `[]` delivers `{}`.
- [ ] **TT-CX-07 — Ordering invariant:** a re-created key appears once and last;
      removing the pop loop changes the resolved shape (T-CX-14's regression
      test).
- [ ] **TT-CX-08 — Non-mutation:** the caller's `input_shapes` dict is identical
      before and after a step executes, including after a deep recursion.
- [ ] **TT-CX-09 — Branch isolation:** a positional slot in the second top-level
      branch raises; a named reference across branches resolves.
- [ ] **TT-CX-10 — Registry accumulation:** a shape produced deep in a branch is
      visible to that branch's later siblings.
- [ ] **TT-CX-11 — `None` `input_shapes`:** the first step of a branch executes
      without a `TypeError`, and a positional slot in it raises.
- [ ] **TT-CX-12 — Identifier collision:** two steps sharing an identifier leave
      only the later shape, without error (or raise, per T-CX-20's decision).
- [ ] **TT-CX-13 — Log level lowered and restored** on the success path.
- [ ] **TT-CX-14 — Log level restored on exception** (T-CX-16's fix).
- [ ] **TT-CX-15 — Log level is never raised:** a creator with a *higher*
      `loglevel` than the ambient level leaves it untouched.
- [ ] **TT-CX-16 — `MutableMapping` protocol** on both node classes: `len`,
      index, iterate, delete, `update`, `in`.
- [ ] **TT-CX-17 — `append` keying:** `parent.append(child)` registers the child
      under `child.creator.identifier`.
- [ ] **TT-CX-18 — Root identifier suffix:** `"x"` → `"x.root"`.
- [ ] **TT-CX-19 — Node identifier delegation:** a step node's identifier equals
      its creator's, and the node never invokes positional resolution.
- [ ] **TT-CX-20 — Abstract enforcement:** a subclass without `_create_shape`
      raises `TypeError` at instantiation.
- [ ] **TT-CX-21 — `JSONStepNode` equivalence:** a sub-tree loaded from a file
      produces the same shapes as the inline equivalent; a missing file and a
      missing `wing_config` both fail at build time with distinguishable errors.
- [ ] **TT-CX-22 — Creator inventory count:** the star-import exposes exactly the
      documented classes; a Creator omitted from its subpackage `__init__.py` is
      detected.
- [ ] **TT-CX-23 — `ted_sketch_creators` dispatch:** each of `middle`, `top`,
      `top_simple` resolves; an unknown hinge type produces the agreed error.
- [ ] **TT-CX-24 — Pass-through Creators:** an export-style Creator returning
      `shapes_of_interest` unchanged leaves the registry content-identical.

## Suggested Order

1. **T-CX-01 → T-CX-05** first. Nothing else can be written or tested without
   the Creator contract. T-CX-03 and T-CX-04 must land together — the guard and
   the lookup are one behaviour split across two methods.
2. **T-CX-14** immediately after T-CX-03, **before** the tree exists. Writing the
   ordering regression test first is what stops step 3 from being subtly wrong.
3. **T-CX-06 → T-CX-08** — the tree. T-CX-07 is the heart of the slice and
   depends on T-CX-03's semantics being settled. T-CX-08 is small but
   load-bearing (T-CX-15).
4. **T-CX-16** with T-CX-02, not later — retrofitting `try/finally` after the
   tests are written invites a test that asserts the broken behaviour.
5. **T-CX-09** after the tree, and after
   [`../json-polymorphic-roundtrip/tasks.md`](../json-polymorphic-roundtrip/tasks.md)
   T-JS-02 (class resolution) exists — `JSONStepNode` cannot decode without it.
6. **T-CX-10 → T-CX-13** — the authoring contract and inventory. T-CX-10 depends
   on the catalogue reflection rules owned by
   [`construction-plans`](../../construction-plans/tasks.md); coordinate rather
   than duplicating. T-CX-12 depends on the registration mechanism
   (`../json-polymorphic-roundtrip/tasks.md` T-JS-02).
7. **T-CX-17 → T-CX-19** — omissions and cosmetic fixes, applied as review gates
   throughout rather than as a phase.
8. **T-CX-20 → T-CX-22** last, and raised with the maintainer **before** the
   corresponding code is written. T-CX-20 in particular interacts with T-CX-14:
   re-creating a key within a branch is supported on purpose, so a blanket
   collision error would be a behaviour change, not a bug fix.

## Pending Gaps

- **Should a duplicated creator identifier be an error?** Today the later shape
  silently overwrites the earlier one. The pop-then-update in
  `ConstructionStepNode` explicitly supports *re-creating* a key within a branch,
  so a blanket raise would break that idiom — the two cases need to be
  distinguished before either is enforced.
- **Should a Creator's return value be validated?** Nothing checks that
  `_create_shape` returned a dict; a list or `None` fails obscurely inside the
  traversal instead of at the Creator's own boundary.
- **Is the private `_create_shape` hook de-facto public?**
  `cad-generation`'s tessellation worker calls
  `WingLoftCreator._create_shape(...)` directly, bypassing the template method.
  Harmless there, but it means at least one consumer depends on the private
  signature.
- **Is concurrent execution within one process supported?** The root logger level
  is mutated globally for the duration of every step — the same unresolved
  tension ADR 0005 records between the process pool and in-process plan
  execution.
- **Should `AbstractConstructionStep` be deleted from the legacy tree?** It is an
  importable abstract class with no implementers, and a future author could
  reasonably implement it and find nothing ever calls `construct`.
- **What should happen for an unknown `hinge_type`?** `ted_sketch_creators` has
  no fallback, and `create_XYZ_ted_sketch` — which looks like it was meant to be
  one — is not in the dispatch dict.
- **Is the missing-keys error message parsed by anything?** Fixing its ordering
  is cosmetic only if no consumer depends on the text.
