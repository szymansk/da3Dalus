# superellipse-xsecs — Implementation Tasks

> Use-case task list, nested under module [`fuselage-design`](../tasks.md).
> Executable sequence to re-implement this slice from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker. Task ids are **slice-local** and map to the module
> list where noted.

## Prerequisites

- [ ] `aeroplane-core` available — every route resolves an aeroplane by UUID,
      and `fuselages` cascade-delete with the aeroplane.
- [ ] `get_db()` request-scoped session owning the transaction
      (`app/db/session.py:55-64`, ADR 0009). The slice never commits.
- [ ] `app/core/exceptions.py` hierarchy plus `_raise_http_from_domain`
      (`aeroplane/base.py:52-67`) — note this slice uses `ConflictError`, which
      the wing equivalent does not.
- [ ] `component_tree_service` reachable for the `fuselage:<name>` group
      auto-sync (gh#108), imported **lazily** to break the cycle.
- [ ] `ARTIFACTS_BASE_DIR` configured and `.resolve()`d
      (`app/core/config.py:24-32`) — the download routes read relative paths
      against it.

No geometry kernel is required for this slice. CadQuery is needed only by
[`step-slicing/`](../step-slicing/tasks.md). 🟢

## Tasks

- [ ] **T-01 — `fuselages` table and `FuselageModel`.** (module T-01)
  Columns: `name` (required), `symmetric` (Boolean, **default `False`**),
  `step_path` (nullable String, relative), `solid_step_path` (nullable String,
  relative), `aeroplane_id` FK → `aeroplanes.id` `ON DELETE CASCADE`.
  - Legacy origin: `app/models/aeroplanemodel.py:526`; `symmetric` rationale at
    `:529-533` (gh-715)
  - Definition of done: a fuselage created without `symmetric` reads back
    `false`, and deleting the aeroplane removes the row.
  - Confidence: 🟢

- [ ] **T-02 — `fuselage_xsecs` table and `FuselageXSecSuperEllipseModel`.**
  (module T-02)
  Columns: `xyz` (JSON `[x,y,z]`, **metres**), `a` (Float, **Y half-axis**, m),
  `b` (Float, **Z half-axis**, m), `n` (Float, exponent), `sort_index`
  (Integer, default 0), `fuselage_id` FK `ON DELETE CASCADE`. Ordered by
  `sort_index`, `cascade="all, delete-orphan"`.
  - Legacy origin: `app/models/aeroplanemodel.py:512`
  - Definition of done: deleting a fuselage removes every cross-section; reads
    come back in `sort_index` order without a caller-side sort.
  - Confidence: 🟢

- [ ] **T-03 — `FuselageSchema` with `min_length=2`.** (module T-03)
  `name`, `x_secs` (**`min_length=2`**), `symmetric: bool = False`,
  `step_path: str | None = None`, `solid_step_path: str | None = None`.
  - Legacy origin: `app/schemas/aeroplaneschema.py:755`
  - Definition of done: a payload with one cross-section is rejected at
    validation time (→ 422), before the service is entered.
  - Confidence: 🟢

- [ ] **T-04 — `FuselageXSecSuperEllipseSchema` and the axis convention.**
  (module T-04)
  `xyz`, `a`, `b`, `n` all required; `a` is the **Y half-axis** mapping to ASB
  `FuselageXSec.width`, `b` the **Z half-axis** mapping to `.height`. Document it
  on the fields — they are **half-axes, not diameters**, and no factor of two is
  applied anywhere.
  - Legacy origin: `app/schemas/aeroplaneschema.py:711-723` (gh-706)
  - Definition of done: a conversion test asserts `width == a` and
    `height == b` (not `2a` / `2b`) on the produced ASB `FuselageXSec`.
  - Confidence: 🟢

- [ ] **T-05 — Superellipse identities available to consumers.**
  Shape law `|y/a|^n + |z/b|^n = 1`; polar form
  `r(θ) = (|cos θ / a|^n + |sin θ / b|^n)^(−1/n)`;
  `perimeter = ∫₀^{2π} sqrt(r² + (dr/dθ)²) dθ` (scipy quad, `limit = 200`);
  `area = 4·a·b·Γ(1 + 1/n)² / Γ(1 + 2/n)`; `polygon_area` = shoelace.
  - Legacy origin: `cad_designer/aerosandbox/slicing.py:585-608`
  - Definition of done: at `n = 2`, `area` reproduces `π·a·b` and `perimeter`
    matches a reference ellipse approximation within tolerance.
  - Confidence: 🟢 (the closed forms); 🟡 (that `n = 2 → π·a·b` — derived, not
    asserted in code)

- [ ] **T-06 — `create_fuselage` with a 409 on duplicates.** (module T-05)
  Persist the fuselage and its ordered cross-sections; a name already present on
  the aeroplane raises `ConflictError` → **409**.
  - Legacy origin: `app/services/fuselage_service.py:63, 80-84`
  - Definition of done: a second create with the same name returns 409
    `conflict`. Record in the test that the wing path answers 422 — see the open
    gap.
  - Confidence: 🟢

- [ ] **T-07 — `update_fuselage` destructive replace.** (module T-06)
  Remove the old `FuselageModel` from the collection and append a brand-new one
  built from the payload.
  - Legacy origin: `fuselage_service.py:103, 120-122`
  - Definition of done: a test **documents** that `step_path` absent from the
    payload is lost after an update. This encodes current behaviour and must be
    changed deliberately if the merge-vs-replace gap is resolved.
  - Confidence: 🟢 (the loss is 🟡 INFERRED consequence)

- [ ] **T-08 — `get_fuselage`, `list_fuselage_names`, `delete_fuselage`.**
  (module T-07)
  Lookup by name under an aeroplane, `NotFoundError` → 404 on a miss; delete
  cascades to the cross-sections.
  - Legacy origin: `fuselage_service.py:45, 137, 160`
  - Definition of done: unknown fuselage name → 404 with the `not_found`
    envelope; delete leaves no `fuselage_xsecs` rows behind.
  - Confidence: 🟢

- [ ] **T-09 — Cross-section CRUD by index.** (module T-08)
  `get_fuselage_cross_sections`, `delete_all_cross_sections`,
  `get_cross_section`, `create_cross_section`, `update_cross_section`,
  `delete_cross_section`.
  - Legacy origin: `fuselage_service.py:193, 219, 244, 276, 327, 364`
  - Definition of done: `DELETE .../cross_sections` empties the stack but keeps
    the fuselage row; an out-of-range index returns 404.
  - Confidence: 🟢 (the exact out-of-range behaviour is 🟡)

- [ ] **T-10 — Component-tree group auto-sync (gh#108).** (module T-09)
  Create/update drive `sync_group_for_fuselage`; delete calls
  `delete_synced_nodes("fuselage:<name>")`, imported lazily to break the
  `fuselage_service ↔ component_tree_service` cycle.
  - Legacy origin: `fuselage_service.delete_fuselage:179-181`
  - Definition of done: a group node with `synced_from = "fuselage:<name>"`
    appears on create and disappears on delete.
  - Confidence: 🟢

- [ ] **T-11 — STEP artefact download routes.** (module T-10)
  `GET .../fuselages/{name}/step` and `.../solid_step` resolve the stored
  **relative** path against `settings.ARTIFACTS_BASE_DIR` and stream the file; a
  `NULL` column yields 404. This slice **never writes** either column.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/fuselages.py:198, 234`;
    `app/core/config.py:24-32`
  - Definition of done: a fuselage without `solid_step_path` returns 404 on
    `/solid_step`; the resolved path never escapes `ARTIFACTS_BASE_DIR`.
  - Confidence: 🟢 (the 404-on-null mapping is 🟡)

- [ ] **T-12 — Symmetry as a consumer contract.**
  Store `symmetric` and publish the `y → −y` duplication rule; do **not**
  materialise a mirrored row. Default `False` because the main fuselage sits on
  the symmetry plane — the opposite of `wings.symmetric`.
  - Legacy origin: `app/models/aeroplanemodel.py:529-533`;
    `app/schemas/aeroplaneschema.py:762-773` (gh-715)
  - Definition of done: a `symmetric = true` fuselage stores exactly one row, and
    a consumer-side test proves the mirrored copy is produced downstream.
  - Confidence: 🟢

- [ ] **T-13 — CRUD routes.** (module T-25, fuselage/xsec portion)
  Exactly as listed in [`../contracts.md`](../contracts.md), with the shared
  domain→HTTP mapping — including the **409** on duplicate create.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/fuselages.py`
  - Definition of done: contract tests assert every status code, notably the 409
    (not 422) on a duplicate name.
  - Confidence: 🟢

- [ ] **T-14 — Geometry-change fan-out.** (module T-27)
  Route fuselage mutations through `invalidation_service.mark_ops_dirty` so
  dependent operating points become `DIRTY`.
  - Legacy origin: `app/services/invalidation_service.py:16-93`
  - Definition of done: creating or deleting a fuselage marks the aircraft's
    non-`DIRTY`/`COMPUTING` operating points `DIRTY`.
  - Confidence: 🟡 INFERRED — the cross-module note states the requirement for
    "any new geometry-mutating path"; the fuselage-side call sites were not
    enumerated.

## Test Tasks

- [ ] **TT-01 — Happy path:** create a fuselage with three cross-sections, read
      it back in `sort_index` order, delete it and assert the cascade.
- [ ] **TT-02 — Failure:** a one-cross-section payload returns 422 before the
      service is entered.
- [ ] **TT-03 — Duplicate name returns 409**, with a note in the test that the
      wing equivalent returns 422.
- [ ] **TT-04 — Unknown name returns 404** with the `not_found` envelope, for
      both the fuselage and a cross-section index.
- [ ] **TT-05 — `symmetric` default is `false`** on a fuselage created without
      the field, in contrast to a wing's `true`.
- [ ] **TT-06 — Symmetry stores one row:** `symmetric = true` does not
      materialise a second, mirrored cross-section stack.
- [ ] **TT-07 — Destructive update:** a `POST` without `step_path` clears the
      stored path. This test **documents** current behaviour.
- [ ] **TT-08 — Update replaces the stack:** three cross-sections replaced by two
      leaves exactly two rows.
- [ ] **TT-09 — Delete-all keeps the fuselage:**
      `DELETE .../cross_sections` empties the stack, the fuselage row survives.
- [ ] **TT-10 — Component-tree sync:** `fuselage:<name>` node appears on create
      and is removed on delete.
- [ ] **TT-11 — STEP download:** a fuselage without `solid_step_path` returns
      404; a present path resolves under `ARTIFACTS_BASE_DIR` and never escapes
      it.
- [ ] **TT-12 — ASB axis mapping:** `width == a` and `height == b` on the
      converted `FuselageXSec` — a factor-of-two regression must fail this test.
- [ ] **TT-13 — Superellipse identities:** `n = 2` gives `area == π·a·b`;
      `perimeter` matches a reference ellipse approximation.
- [ ] **TT-14 — Ordering:** cross-sections created out of order come back sorted
      by `sort_index`.

## Data Migration Tasks

- [ ] **TM-01 — Verify the half-axis interpretation of existing rows.**
  (module TM-01) If any historical importer wrote full widths instead of
  half-axes, those fuselages are twice their intended size. 🟢 **Method decided**
  (`Q-FD-3`): compare `2a ≤ 1.02·Y_extent(step)` and `2b ≤ 1.02·Z_extent(step)`
  per xsec where a `step_path` survives — this catches the factor-2 error. Add
  `max_x(2a)/max_x(2b)` within 20 % of `Y_extent/Z_extent` for the whole body to
  catch an `a ↔ b` **swap**, which no integral metric can see (a swap leaves
  volume and wetted area near-unchanged, exactly unchanged for a body of
  revolution). Where no `step_path` exists, fall back to the aspect-ratio band
  `2a/2b ∈ [0.3, 3.0]` as a **warning only**, never a rejection.
- [ ] **TM-02 — Audit `symmetric` on imported sub-fuselages.** (module TM-03)
  Rows imported before gh-715 default to `False`, so paired gear struts and
  fairings would render on one side only. 🟡
- [ ] **TM-03 — Detect fuselages left with fewer than two cross-sections.**
  `min_length=2` is a schema rule, not a database constraint, so rows written
  before it — or through `delete_all_cross_sections` — may violate it. Decide
  repair-vs-delete. 🟡

## Suggested Order

1. **T-01 → T-05** first — the two tables, the two schemas and the superellipse
   identities. **T-04's axis convention must be settled before anything else**: a
   swapped or doubled `a`/`b` is silent and corrupts every downstream consumer.
   T-05 is pure mathematics and needs no database.
2. **T-06 → T-09** next — the lifecycle. T-06 blocks T-07 and T-08 (nothing to
   update or delete without a create). T-07 deliberately encodes existing
   behaviour; do **not** "fix" it while the merge-vs-replace gap is open.
3. **T-10** after T-06…T-09, because it hooks into all three write paths and
   depends on `aeroplane-core`'s component tree existing.
4. **T-11 → T-12** — the artefact pointers and the symmetry contract. T-11 needs
   `ARTIFACTS_BASE_DIR` from the prerequisites but nothing from steps 2-3;
   T-12 is a documentation-plus-default task with a consumer-side assertion.
5. **T-13 → T-14** last — the REST layer is thin and only wires what is already
   tested. T-14 needs `invalidation_service` to exist.

## Pending Gaps (🔴)

- **Should the `a`/`b` ↔ `width`/`height` mapping be asserted at runtime?** A
  swap produces a plausible-looking but 90°-rotated body, and a doubling
  produces an oversized one, with no error in either case. The convention lives
  only in field descriptions.
- **Should `update_fuselage` merge instead of replace?** Today a partial payload
  silently drops `step_path` / `solid_step_path`, and the operation still
  returns 200.
- **Duplicate-name status divergence:** fuselages answer 409, wings answer 422
  for the same condition. Which is correct, and should the other change?
- **Should there be a maximum cross-section count?** `min_length=2` is enforced;
  no upper bound was found, so a pathological payload is limited only by request
  size.
- **Should a failing component-tree sync block a fuselage delete?** The lazy
  import here is for cycle-breaking only, with no `try/except`, unlike
  `aeroplane-core`'s explicitly best-effort `_sync_aircraft_mass`.
