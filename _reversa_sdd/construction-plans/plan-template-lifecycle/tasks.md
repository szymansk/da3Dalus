# plan-template-lifecycle — Implementation Tasks

> Executable sequence to re-implement this use case from the legacy behaviour.
> Nested under the module [`construction-plans`](../tasks.md).
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.

## Prerequisites

- [ ] `aeroplane-core` reachable — `instantiate_template` and the aeroplane-scoped
      listing both resolve an aeroplane by UUID first.
- [ ] `get_db()` request-scoped session owning the transaction (ADR 0009), with
      `autoflush=False`. Services call `db.flush()`, never `commit()`.
- [ ] `app/core/exceptions.py` — `NotFoundError`, `ValidationError`.
- [ ] `sqlalchemy.orm.attributes.flag_modified` available (JSON-column mutation).
- [ ] The `$TYPE` dialect definition from `cad-designer-topology` — this slice
      stores it and knows exactly one fact about it (a root node carries no
      `creator` key).

## Tasks

### Schema

- [ ] **T-PT-01 — The `construction_plans` table.**
  `id` PK · `name` String (not unique) · `description` · `tree_json` JSON ·
  `plan_type` String `server_default "template"` · `aeroplane_id` FK →
  `aeroplanes.id` (nullable) · `created_at` · `updated_at` (`onupdate`).
  - Legacy origin: `app/models/construction_plan.py:11`;
    `alembic/versions/b3e2f1a4c7d9_add_construction_plans_table.py`,
    `c4d5e6f7a8b9_add_plan_type_and_aeroplane_id.py`
  - Definition of done: a template stores `aeroplane_id IS NULL`; a plan stores a
    reference; `tree_json` round-trips without key reordering damage.
  - Confidence: 🟢

- [ ] **T-PT-02 — Settle the `aeroplane_id` column type first.**
  The legacy column is a `String` FK against the `Integer` `aeroplanes.id`, with
  no `ON DELETE`. Decide the target (integer `id` or public `uuid`) and make the
  types match.
  - Legacy origin: `app/models/construction_plan.py`; data-dictionary
    §Table `construction_plans`
  - Definition of done: the schema is creatable on PostgreSQL, not only SQLite,
    and deleting an aeroplane has a defined, tested effect on its plans.
  - Confidence: 🟡 — blocking decision (see § Pending Gaps).

- [ ] **T-PT-03 — Decide whether `plan_type` gets an enum or check constraint.**
  Free text today. A typo yields a row that neither instantiates nor is
  recognised as a template by `execute_plan`.
  - Legacy origin: no constraint in either migration
  - Definition of done: either a constraint plus a migration validating existing
    values, or a written decision to keep it open.
  - Confidence: 🟡 — needs a human decision.

### Validation and shape

- [ ] **T-PT-04 — `_validate_tree_json`.**
  Raise `ValidationError` unless the **root** dict has `$TYPE` **and**
  `creator_id`. Inspect nothing deeper.
  - Legacy origin: `construction_plan_service.py:72-81`
  - Definition of done: a root missing either key returns 422 naming the missing
    field and writes no row; a root that is valid but whose *child* references an
    unknown `$TYPE` is accepted (the failure belongs to execution — BR-70).
  - Confidence: 🟢

- [ ] **T-PT-05 — Run the validation on update as well as create.**
  - Legacy origin: `construction_plan_service.py` (`create_plan`, `update_plan`)
  - Definition of done: a `PUT` that replaces a valid root with an invalid one
    returns 422 and leaves the stored row untouched.
  - Confidence: 🟢

- [ ] **T-PT-06 — `_count_steps` over both successor encodings.**
  Read `successors`; iterate `.values()` when it is a dict, the sequence itself
  when it is a list; count each dict node once and recurse. The root is not
  counted. Non-dict list entries are skipped, not an error.
  - Legacy origin: `construction_plan_service.py:38-53`
  - Definition of done: a root with two children (one of which has one child)
    reports `3`; the dict-encoded and list-encoded forms of the same tree agree;
    a list containing a bare string does not raise.
  - Confidence: 🟢

### The legacy root migration

- [ ] **T-PT-07 — Reproduce the migration transformation exactly.**
  A root whose `$TYPE` is `"ConstructionStepNode"` becomes
  `"ConstructionRootNode"` and loses its `creator` key. Nothing else changes; a
  root that is already correct is a no-op.
  - Legacy origin: `construction_plan_service.py:113-133`
  - Definition of done: a unit test over a real legacy tree asserts both the
    rewritten `$TYPE` and the removed key, and asserts that a correct root is
    returned byte-identical.
  - Confidence: 🟢

- [ ] **T-PT-08 — Use `flag_modified` (or an equivalent) when mutating the JSON
  column.**
  Mutating a JSON column in place does not mark the attribute dirty; without the
  hint the rewrite is silently lost.
  - Legacy origin: `construction_plan_service.py:113-133`
  - Definition of done: a test that migrates, commits, expires the session and
    re-reads confirms the change was persisted.
  - Confidence: 🟢

- [ ] **T-PT-09 — Move the migration off the read path.**
  Legacy behaviour runs it inside `get_plan`, so a plain `GET` can issue an
  `UPDATE` and — via `get_db()`'s commit-on-success — commit it. Run the
  transformation once, as a data migration (see TM-PT-01), and make `get_plan` a
  pure read.
  - Legacy origin: `construction_plan_service.py:113-133` called from `get_plan`
  - Definition of done: reading a plan issues no `UPDATE`; the read path has no
    write. Do **not** reproduce the lazy form.
  - Confidence: 🟢 on the defect, and 🟢 on disposition (`R2-02`): legacy roots cannot arrive after the migration; the lazy path is deleted. **Guard required:** a legacy root arriving later (restored backup, hand-written JSON) must produce a legible error naming plan, step and unrecognised shape (`P-WARN-0`), not a bare `AttributeError`
    from an external source (see § Pending Gaps).

### CRUD

- [ ] **T-PT-10 — `get_plan` / `list_plans` / `create_plan` / `update_plan` /
  `delete_plan`.**
  `get_plan` raises `NotFoundError` when absent. `list_plans` takes an optional
  `plan_type` filter. `create_plan` and `update_plan` validate the root first.
  `delete_plan` is a hard delete of the row only.
  - Legacy origin: `construction_plan_service.py` (CRUD block);
    `app/api/v2/endpoints/construction_plans.py:67-154`
  - Definition of done: the five operations answer 200 / **201** / **204** / 404
    / 422 exactly as `../contracts.md` states.
  - Confidence: 🟢

- [ ] **T-PT-11 — `_to_summary` with `step_count`.**
  `PlanSummary(id, name, description, step_count, plan_type, aeroplane_id,
  created_at)`; `PlanRead` is `model_validate(plan, from_attributes=True)`.
  - Legacy origin: `construction_plan_service.py:56-69`
  - Definition of done: list views carry `step_count`; detail views carry the
    full `tree_json`.
  - Confidence: 🟢

- [ ] **T-PT-12 — Decide what happens to a deleted plan's artefacts.**
  `delete_plan` removes the row only; directories under
  `<aeroplane>/<plan_id>/` survive and become unreachable through the API.
  - Legacy origin: `delete_plan` (no `artifact_service` call)
  - Definition of done: either a cascading artefact delete or a documented,
    tested retention decision.
  - Confidence: 🟡 — needs a human decision.

### Template duality

- [ ] **T-PT-13 — `instantiate_template`.**
  Assert `plan_type == "template"` (else `ValidationError` → 422), assert the
  aeroplane exists (else `NotFoundError` → 404), `copy.deepcopy` the tree, name
  the result `name or f"{template.name} — Plan"` (literal em dash), set
  `plan_type = "plan"` and the aeroplane id. Record **no** back-link.
  - Legacy origin: `construction_plan_service.py:207-232`
  - Definition of done: mutating the instance's tree leaves the template
    byte-identical; instantiating a `"plan"` returns 422; instantiating under a
    missing aeroplane returns 404.
  - Confidence: 🟢

- [ ] **T-PT-14 — `to_template`.**
  `copy.deepcopy` the tree, name it `name or f"{plan.name} — Template"`, set
  `plan_type = "template"` and `aeroplane_id = None`. Note the legacy asymmetry:
  this operation does **not** assert the source type.
  - Legacy origin: `construction_plan_service.py:235-251`
  - Definition of done: the result is an unbound template; the derived names
    compound as `"X" → "X — Plan" → "X — Plan — Template"`.
  - Confidence: 🟢 (whether the missing assertion is intended: 🟡)

- [ ] **T-PT-15 — Optional-body name override on both conversions.**
  `InstantiateRequest` / `ToTemplateRequest` each carry a single optional
  `name`; the request body itself is optional on both routes.
  - Legacy origin: `app/schemas/construction_plan.py:53, 59`;
    `aeroplane_construction_plans.py:55-78, 134-150`
  - Definition of done: `POST` with no body succeeds and uses the derived name;
    `{"name": "X"}` yields exactly `X`.
  - Confidence: 🟢

### REST layer

- [ ] **T-PT-16 — The CRUD and duality routes.**
  `GET|POST /construction-plans`, `GET|PUT|DELETE /construction-plans/{plan_id}`,
  `GET /aeroplanes/{id}/construction-plans`,
  `POST /aeroplanes/{id}/construction-plans/from-template/{template_id}`,
  `POST /aeroplanes/{id}/construction-plans/{plan_id}/to-template`,
  `GET|POST /construction-templates` — with the status codes from
  `../contracts.md` (**201** on create/instantiate/lift, **204** on delete).
  - Legacy origin: `construction_plans.py:67-154`,
    `aeroplane_construction_plans.py:39-78, 134-150`,
    `construction_templates.py:36-65`
  - Definition of done: a contract test asserts every method, path and status
    code, including that `DELETE` is 204 and not 200.
  - Confidence: 🟢

- [ ] **T-PT-17 — Declare `/construction-plans/creators` before
  `/construction-plans/{plan_id}`.**
  A constraint imposed by the sibling catalog slice but enforced in this
  router's declaration order; reversed, `"creators"` is captured as a plan id.
  - Legacy origin: `construction_plans.py:51-59` (in-code comment)
  - Definition of done: a test calls `/creators` and asserts a list, not an
    int-parse failure.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-PT-01 — Happy path:** create a template, read it back, and assert
      `plan_type == "template"` with `aeroplane_id IS NULL`.
- [ ] **TT-PT-02 — Failure:** a root missing `$TYPE`, and a root missing
      `creator_id`, each return 422 and write no row.
- [ ] **TT-PT-03 — Deferred failure:** a root that is valid but whose child
      references an unknown `$TYPE` is stored with 201 (BR-70).
- [ ] **TT-PT-04 — Update re-validates:** a `PUT` with an invalid root returns
      422 and leaves the stored row unchanged.
- [ ] **TT-PT-05 — Deep-copy independence:** mutating an instantiated plan's tree
      leaves the template byte-identical, and vice versa for `to_template`.
- [ ] **TT-PT-06 — Instantiation guards:** a `"plan"` source → 422; a missing
      aeroplane → 404; neither writes a row.
- [ ] **TT-PT-07 — Derived names compound:** `"X"` → `"X — Plan"` →
      `"X — Plan — Template"`, with the literal em dash.
- [ ] **TT-PT-08 — Name override** wins over the derived name on both routes, and
      an absent body is accepted.
- [ ] **TT-PT-09 — Migration transformation:** a `ConstructionStepNode` root
      becomes `ConstructionRootNode` without its `creator` key; an already-correct
      root is returned byte-identical.
- [ ] **TT-PT-10 — Migration persists:** after migrating, committing and
      expiring the session, the re-read row carries the migrated shape.
- [ ] **TT-PT-11 — Read is pure:** reading a plan issues no `UPDATE` (the legacy
      code fails this test by construction — it is the target behaviour).
- [ ] **TT-PT-12 — `step_count` parity:** dict-encoded and list-encoded successors
      of the same tree report the same number; the root is not counted; a list
      containing a bare string does not raise.
- [ ] **TT-PT-13 — Discriminator filter:** `?plan_type=template` returns only
      templates; `?plan_type=plan` only plans; no filter returns both.
- [ ] **TT-PT-14 — Aeroplane scoping:** `GET /aeroplanes/{id}/construction-plans`
      returns only that aeroplane's plans and never a template.
- [ ] **TT-PT-15 — Status codes:** create → 201, delete → 204, instantiate → 201,
      to-template → 201, unknown id → 404.
- [ ] **TT-PT-16 — Route ordering:** `/construction-plans/creators` resolves to
      the catalog, not to a plan lookup.

## Data Migration Tasks

- [ ] **TM-PT-01 — Run the root migration once, as an Alembic data migration.**
      Rewrite every `construction_plans` row whose `tree_json["$TYPE"]` is
      `"ConstructionStepNode"`, then delete the read-path call. Log the count of
      rewritten rows in the migration output — the lazy path leaves no audit
      trail, so this is the only record that will ever exist. 🟡
- [ ] **TM-PT-02 — Repair `construction_plans.aeroplane_id`.** Decide the target
      column (`aeroplanes.id` Integer or `aeroplanes.uuid` String), convert
      existing values, fix the FK type and add an `ON DELETE` behaviour. Until
      then the schema is SQLite-only. 🔴
- [ ] **TM-PT-03 — Audit rows for an inconsistent discriminator.** Because
      `plan_type` is free text and `aeroplane_id` is optional, three invalid
      combinations already exist as possibilities: `plan_type == "plan"` with a
      null aeroplane, `plan_type == "template"` with a non-null aeroplane, and
      any other string. Report the counts before deciding T-PT-03. 🟡
- [ ] **TM-PT-04 — Reconcile orphaned artefact directories** whose `plan_id` no
      longer exists, once the retention decision in T-PT-12 is made. 🟡

## Suggested Order

1. **T-PT-01 → T-PT-03** first — the table and its two 🔴 schema decisions.
   Settling the FK type and the discriminator constraint before any service code
   is written avoids a second migration and a second round of tests.
2. **T-PT-04 → T-PT-06** next: validation and `step_count` are pure functions
   with no dependencies, cheap to test, and every other task builds on the
   validation contract.
3. **T-PT-07 → T-PT-09 plus TM-PT-01** as one unit. Reproduce the transformation
   (T-PT-07), get the persistence mechanics right (T-PT-08), then run it once and
   remove it from the read path (T-PT-09 / TM-PT-01). Doing T-PT-09 before
   TM-PT-01 would make legacy plans unreadable in the interim.
4. **T-PT-10 → T-PT-12** — CRUD. T-PT-10 depends on T-PT-04 (validation) and
   T-PT-09 (a pure `get_plan`). T-PT-12 is a decision that can run in parallel.
5. **T-PT-13 → T-PT-15** — the duality. Both conversions depend on `get_plan`
   from T-PT-10 and on the aeroplane lookup from `aeroplane-core`.
6. **T-PT-16 → T-PT-17** last — the REST layer is thin and only wires what is
   already tested. T-PT-17 is a one-line constraint that is expensive to discover
   later.

## Pending Gaps

- **Which column is `aeroplane_id` meant to reference — `aeroplanes.id`
  (Integer) or `aeroplanes.uuid` (String)?** The current `String` → `Integer` FK
  is valid only under SQLite's dynamic typing, and there is no `ON DELETE`
  (T-PT-02, TM-PT-02).
- **May the read-path migration be removed after a one-off data migration**, or
  do legacy roots still arrive from an external source (an import, a fixture, a
  hand-edited payload)? Today it rewrites on every read, with no marker and no
  log (T-PT-09, TM-PT-01).
- **Should `plan_type` be constrained?** It is free text with no enum and no
  check constraint, so a typo produces a row that neither instantiates nor is
  treated as a template by the executor (T-PT-03).
- **Should `PlanCreate` require `aeroplane_id` when `plan_type == "plan"`?**
  An unbound "plan" row is creatable today and fails only at execution.
- **Should a plan record the template it came from?** BR-69 makes divergence
  deliberate, but with no back-link a template fix cannot be propagated and a
  template's instances cannot be enumerated. Combined with the non-unique `name`,
  repeated instantiation produces indistinguishable rows.
- **Is `to_template`'s missing source-type assertion intended?** It accepts a
  template as input and simply duplicates it, unlike `instantiate_template`,
  which asserts.
- **What happens to a deleted plan's artefacts?** The row goes, the directories
  under `<aeroplane>/<plan_id>/` stay, and they become unreachable through the
  API (T-PT-12, TM-PT-04).
