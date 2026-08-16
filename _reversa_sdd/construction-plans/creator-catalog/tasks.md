# creator-catalog — Implementation Tasks

> Executable sequence to re-implement this use case from the legacy behaviour.
> Nested under the module [`construction-plans`](../tasks.md).
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.

## Prerequisites

- [ ] `cad-designer-topology` importable **or** cleanly absent —
      `AbstractShapeCreator` plus the five Creator subpackages
      (`cad_operations`, `components`, `export_import`, `fuselage`, `wing`),
      each re-exporting its classes from its `__init__.py`. An `ImportError` is a
      **supported** state, not a failure (ADR 0017).
- [ ] The Creator docstring conventions of
      `cad_designer/airplane/creator/_creator_template.py` — the `Attributes:`
      and `Returns:` blocks and the `suggested_creator_id` class attribute. This
      slice **reads** them; it cannot enforce them (the layer is frozen).
- [ ] `app/schemas/construction_plan.py` — `CreatorParam`, `CreatorOutput`,
      `CreatorInfo`.
- [ ] Python `inspect` and `typing` (`get_origin` / `get_args`) — no third-party
      reflection library is used.

## Tasks

### Reflection walk

- [ ] **T-CC-01 — `list_creators` with the inline platform guard.**
  Import `AbstractShapeCreator` **and** `cad_designer.airplane.creator` (the
  latter for its subclass-registering side effect); on `ImportError` return `[]`.
  Then walk and sort by `(category, class_name)`.
  - Legacy origin: `construction_plan_service.py:483-504` (ADR 0017)
  - Definition of done: with `cad_designer` unimportable the route answers
    **200 `[]`** — never 500, never 503; with it importable, every registered
    Creator appears exactly once, in a stable order across two calls.
  - Confidence: 🟢

- [ ] **T-CC-02 — `_collect_creators` — skip but recurse.**
  Recurse `cls.__subclasses__()`. Do not emit an entry for
  `ConstructionRootNode`, `ConstructionStepNode` or `JSONStepNode`, but **do**
  recurse into their subclasses.
  - Legacy origin: `construction_plan_service.py:507-553`
  - Definition of done: the three names are absent from the output, and a test
    Creator whose base is `ConstructionStepNode` is present.
  - Confidence: 🟢

- [ ] **T-CC-03 — Make one malformed Creator non-fatal.**
  Legacy has no per-class guard, so an annotation `typing.get_origin` cannot
  handle takes the whole endpoint down with a 500 instead of omitting one entry.
  - Legacy origin: absence of a `try/except` inside `_collect_creators:507-553`
  - Definition of done: with one Creator deliberately broken, the catalog still
    returns every other entry and logs the failure. Do **not** reproduce the
    all-or-nothing behaviour.
  - Confidence: 🟢 on the defect, 🟡 on whether the broken entry should also be
    surfaced to the client.

### Parameter derivation

- [ ] **T-CC-04 — `_INTERNAL_PARAMS` filtering.**
  Hide `self, loglevel, kwargs, creator_id, wing_config, printer_settings,
  servo_information, engine_information, component_information` — exactly
  *framework arguments* ∪ *decoder-injected kwargs*.
  - Legacy origin: `construction_plan_service.py:257-268`
  - Definition of done: a Creator taking `wing_config` and `creator_id` exposes
    neither; every other parameter is exposed.
  - Confidence: 🟢

- [ ] **T-CC-05 — `required` and `default` from the signature.**
  `required = p.default is inspect.Parameter.empty`; `default = None` when
  required, otherwise the literal default.
  - Legacy origin: `construction_plan_service.py:507-553`
  - Definition of done: a parameter with no default reports
    `required: true, default: null`; one with `= 0.1` reports
    `required: false, default: 0.1`.
  - Confidence: 🟢

- [ ] **T-CC-06 — `_type_to_str` with generics resolved first.**
  Handle generic aliases **before** falling back to `__name__`, because
  `list[ShapeId].__name__ == "list"` loses the subscript. Then strip the
  `typing.` and `cad_designer.airplane.types.` prefixes. An unannotated parameter
  renders as `"Any"`.
  - Legacy origin: `construction_plan_service.py:423-436`
  - Definition of done: `list[ShapeId]` renders as `list[ShapeId]`;
    `Optional[float]` carries no `typing.` prefix; `WingSides` carries no
    `cad_designer.airplane.types.` prefix; an unannotated parameter renders
    `"Any"` rather than raising.
  - Confidence: 🟢

- [ ] **T-CC-07 — `_extract_literal_values` through every wrapping.**
  `Literal`, `Optional[Literal]`, `Annotated[Literal]` and nested unions, flattened
  to `list[str]`. A non-literal parameter returns **`None`**, not `[]`.
  - Legacy origin: `construction_plan_service.py:450-480`
  - Definition of done: `WingSides` → `["LEFT","RIGHT","BOTH"]`;
    `Optional[Literal["flat","round"]]` → `["flat","round"]`; `float` → `None`.
    A test asserts `None` and `[]` are distinguishable in the serialised
    response.
  - Confidence: 🟢

### Docstring metadata

- [ ] **T-CC-08 — Class description = first docstring line.**
  - Legacy origin: `construction_plan_service.py:507-553`
  - Definition of done: a multi-line docstring yields only its first line; an
    absent or blank docstring yields `null`.
  - Confidence: 🟢

- [ ] **T-CC-09 — `_parse_docstring_attributes`.**
  Locate the `Attributes:` block and match each line against
  `(\w+)\s*\([^)]*\)\s*:\s*(.*)`, i.e. `name (type): text`. The declared type in
  parentheses is **discarded** — the signature is the type source.
  - Legacy origin: `construction_plan_service.py:330-359`
  - Definition of done: `offset (float): distance in millimetres` attaches that
    text to the `offset` parameter; a documented name absent from the signature
    is ignored; a signature parameter absent from the block gets `null`.
  - Confidence: 🟢

- [ ] **T-CC-10 — `_parse_docstring_returns`.**
  Locate the `Returns:` block and emit `CreatorOutput(key, description)` for each
  entry, with keys such as `{id}` and `{id}.cape`.
  - Legacy origin: `construction_plan_service.py:362-403`
  - Definition of done: a Creator documenting `{id}.cape` reports that key with
    its text; a Creator with no `Returns:` block reports `[]`.
  - Confidence: 🟢

- [ ] **T-CC-11 — Tolerate an undocumented or unconventional Creator.**
  No docstring, an empty docstring, an `Attributes:` header with no conforming
  lines, and a `Returns:` header with no entries must all degrade to
  `null` / `[]` rather than raising.
  - Legacy origin: `construction_plan_service.py:330-359, 362-403`
  - Definition of done: each of the four shapes is covered by a test and none
    raises.
  - Confidence: 🟡 — the empty-section variants were not exercised in the legacy
    tests.

- [ ] **T-CC-12 — `suggested_creator_id` verbatim.**
  `getattr(cls, "suggested_creator_id", None)`, returned with its `{param}`
  placeholders **unresolved** — the decoder substitutes them later from sibling
  parameter values.
  - Legacy origin: `construction_plan_service.py:507-553`
  - Definition of done: `"{wing_index}.vase_wing"` is returned exactly as
    written; a Creator without the attribute reports `null`.
  - Confidence: 🟢

### Category and ordering

- [ ] **T-CC-13 — `_CATEGORY_MAP` by module path.**
  `.creator.wing` → `wing`, `.creator.fuselage` → `fuselage`,
  `.creator.cad_operations` → `cad_operations`, `.creator.export_import` →
  `export_import`, `.creator.components` → `components`; anything else →
  `"other"`.
  - Legacy origin: `construction_plan_service.py:406-420`
  - Definition of done: one Creator per mapped subpackage reports its category,
    and a Creator outside them reports `other`.
  - Confidence: 🟢

- [ ] **T-CC-14 — Deterministic ordering.**
  Sort by `(category, class_name)` explicitly, never relying on
  subclass-registration order.
  - Legacy origin: `construction_plan_service.py:483-504`
  - Definition of done: two consecutive calls return identical ordering, and the
    ordering is independent of import order.
  - Confidence: 🟢

### REST layer

- [ ] **T-CC-15 — `GET /construction-plans/creators`, declared before
  `/{plan_id}`.**
  Reversed, the literal `"creators"` is captured as an integer `plan_id` and the
  catalog becomes unreachable.
  - Legacy origin: `construction_plans.py:51-59` (the in-code comment states the
    requirement) and `:53-65`
  - Definition of done: a test calls `/construction-plans/creators` and asserts a
    list — not a 422 from parsing `"creators"` as an integer. The ordering
    constraint is pinned by that test, not only by a comment.
  - Confidence: 🟢

- [ ] **T-CC-16 — Decide whether the empty catalog should carry a reason.**
  `ImportError` → `[]` with a 200 today, silently: an empty gallery on a machine
  without CadQuery is indistinguishable from a genuinely empty Creator set.
  - Legacy origin: `construction_plan_service.py:483-504`
  - Definition of done: either a documented decision to keep it silent, or a
    signal (a log line at minimum, or a response field) that distinguishes
    "unavailable" from "none registered".
  - Confidence: 🟡 — needs a human decision.

## Test Tasks

- [ ] **TT-CC-01 — Happy path:** with the Creator subpackages importable, the
      route returns 200 and every registered Creator appears exactly once.
- [ ] **TT-CC-02 — Failure / degradation:** with `cad_designer` unimportable the
      route returns 200 and `[]` — not a 500 and not a 503.
- [ ] **TT-CC-03 — Skip list:** `ConstructionRootNode`, `ConstructionStepNode`
      and `JSONStepNode` are absent from the output.
- [ ] **TT-CC-04 — Recurse through the skip:** a Creator subclassing
      `ConstructionStepNode` is present.
- [ ] **TT-CC-05 — Internal parameters hidden:** none of the nine
      `_INTERNAL_PARAMS` names appears on any entry.
- [ ] **TT-CC-06 — Required/default matrix:** no default →
      `required: true, default: null`; `= 0.1` → `required: false, default: 0.1`.
- [ ] **TT-CC-07 — Generic subscript survives:** `list[ShapeId]` renders as
      `list[ShapeId]`, not `list`.
- [ ] **TT-CC-08 — Prefix stripping:** no type string contains `typing.` or
      `cad_designer.airplane.types.`.
- [ ] **TT-CC-09 — Unannotated parameter** renders `"Any"` and does not raise.
- [ ] **TT-CC-10 — Literal matrix:** `WingSides` → three values;
      `Optional[Literal[...]]` → its values; `Annotated[Literal[...], ...]` → its
      values; `float` → `None`.
- [ ] **TT-CC-11 — `None` vs `[]` distinction** survives JSON serialisation.
- [ ] **TT-CC-12 — Description:** first docstring line only; absent docstring →
      `null`.
- [ ] **TT-CC-13 — Attributes parsing:** a documented parameter carries its text;
      a documented name absent from the signature is ignored; a signature
      parameter absent from the block carries `null`; the declared type in
      parentheses does not override the signature type.
- [ ] **TT-CC-14 — Returns parsing:** `{id}.cape` is reported with its text; no
      `Returns:` block → `[]`.
- [ ] **TT-CC-15 — Malformed docstring matrix:** no docstring, empty docstring,
      empty `Attributes:` section, empty `Returns:` section — none raises.
- [ ] **TT-CC-16 — `suggested_creator_id`** is returned unresolved; absent →
      `null`.
- [ ] **TT-CC-17 — Category matrix:** one Creator per mapped subpackage plus one
      outside them → `other`.
- [ ] **TT-CC-18 — Ordering** is stable across calls and independent of import
      order.
- [ ] **TT-CC-19 — Route ordering:** `/construction-plans/creators` resolves to
      the catalog, not to a plan lookup.
- [ ] **TT-CC-20 — One broken Creator does not empty the catalog** (target
      behaviour; the legacy code fails this by construction).
- [ ] **TT-CC-21 — Catalog/decoder agreement:** every `class_name` the catalog
      reports can be resolved by `GeneralJSONDecoder` — the two share one
      registration rule, and a drift between them would let a user author an
      undecodable plan from the gallery.

## Data Migration Tasks

None. This slice is pure reflection over live classes and owns no persistent
state.

> The related corpus problem — nine removed Creator classes still referenced by
> three shipped plan JSONs under `components/constructions/` — belongs to
> `cad-designer-topology` (see its `tasks.md` § Data Migration Tasks). It is
> visible here only as its mirror image: those `$TYPE` names no longer appear in
> the catalog, which is exactly why the plans referencing them cannot decode.

## Suggested Order

1. **T-CC-01 → T-CC-02** first — the walk and the platform guard are the skeleton
   everything else fills in, and T-CC-01's `[]` path is the single most important
   behaviour in this slice.
2. **T-CC-06 → T-CC-07** next, before the rest of the parameter work: both are
   pure functions, trivially unit-testable in isolation, and T-CC-06's
   generics-first ordering is the easiest thing in this slice to get subtly
   wrong.
3. **T-CC-04 → T-CC-05** — the remaining parameter derivation, which depends on
   T-CC-06/T-CC-07 for the fields it fills.
4. **T-CC-08 → T-CC-12** — docstring metadata, independent of the type work and
   parallelisable with steps 2–3. T-CC-11 is a hardening pass over T-CC-09 and
   T-CC-10 and should follow both.
5. **T-CC-13 → T-CC-14** — category and ordering, which complete `CreatorInfo`.
6. **T-CC-03** after the walk is correct: adding the per-class guard is easier to
   verify once there is a known-good baseline to compare against.
7. **T-CC-15 → T-CC-16** last. T-CC-15 is a one-line declaration-order constraint
   that must be pinned by a test rather than a comment; T-CC-16 is a 🔴 decision
   that can be settled in parallel at any point.

## Pending Gaps

- **Should an empty catalog explain itself?** `ImportError` → `[]` with a 200 is
  deliberate and survivable, but a user on `linux/aarch64` sees an empty plan
  editor with no indication that the CAD library is missing rather than that no
  Creators exist. Every other capability-gated route returns a clean 503
  (ADR 0017); this one intentionally does not (T-CC-16).
- **Should the docstring conventions be enforced anywhere?** `_creator_template.py`
  documents `Attributes:`, `Returns:` and `suggested_creator_id`, and nothing
  validates them, so a Creator can ship an undocumented parameter that renders as
  a bare field with no tooltip. Enforcement would have to live in
  `cad-designer-topology`, which is frozen (ADR 0002) — so the question is
  whether a lint step outside that layer is wanted instead.
- **Should a docstring's declared type be cross-checked against the signature?**
  `_parse_docstring_attributes` discards the type in the parentheses, so a
  docstring saying `offset (int)` for a `float` parameter is never flagged and
  the mismatch is invisible to both author and user.
- **Is positional categorisation acceptable?** Category comes from the module
  path with no per-class override, so moving a Creator between subpackages
  silently reclassifies it in the gallery with no deprecation path.
- **Should `creator_id` be exposed as a parameter?** It is hidden by
  `_INTERNAL_PARAMS` even though the user does choose it — it is edited as the
  step's identity in the plan editor. Reasonable, but it means the catalog is not
  a complete description of everything a step needs.
