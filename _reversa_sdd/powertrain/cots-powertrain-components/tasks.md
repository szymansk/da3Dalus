# cots-powertrain-components — Implementation Tasks

> Executable sequence to re-implement the use case from the legacy behaviour.
> Every task cites the legacy file, a definition of done, and a confidence
> marker. Parent module tasks: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] `get_db()` request-scoped session (ADR 0009).
- [ ] `app/core/exceptions.py` with `NotFoundError`, `ValidationError`,
      `ConflictError`, `InternalError`.
- [ ] A startup hook that can run `seed_default_types` unconditionally.
- [ ] The committed COTS snapshots in `data/cots/` for T-09.
- [ ] An artefact store for the 3D-model upload path (T-10 only).

## Tasks

- [ ] **T-01 — `components` table.**
  `name`, `component_type` (indexed String), `manufacturer`, `description`,
  `mass_g` (nullable Float, **grams**), `bbox_{x,y,z}_mm`, `model_ref`,
  `specs` (JSON default `{}`), `created_at` / `updated_at` (tz-aware, onupdate).
  - Legacy origin: `app/models/component.py:8`
  - Definition of done: a component created without a mass keeps `mass_g = NULL`
    — a test must fail if it is coerced to `0`.
  - Confidence: 🟢

- [ ] **T-02 — `component_types` table with the `schema_def` mapping.**
  `name` UNIQUE INDEXED, `label`, `description`, `schema` JSON **mapped to the
  Python attribute `schema_def`**, `deletable` Boolean default `True`
  (`server_default="1"`), timestamps.
  - Legacy origin: `app/models/component_type.py:20, 28`
  - Definition of done: a test asserts the column is `schema` and the attribute
    is `schema_def`, and that a Pydantic model serialising the ORM object does
    not collide with `BaseModel.schema`.
  - Confidence: 🟢

- [ ] **T-03 — `PropertyDefinition` schema.**
  `name`, `label`, `type ∈ {number, string, boolean}`, `unit?`, `required`,
  `min?`, `max?`, `options?`.
  - Legacy origin: `app/schemas/component_type.py`
  - Definition of done: the list round-trips through the JSON column unchanged.
  - Confidence: 🟢

- [ ] **T-04 — `validate_specs`.**
  Unknown type → `ValidationError` naming `GET /component-types`; per property:
  required-and-absent → reason `missing_required`; wrong python type (including
  `bool` supplied for a `number` — Python's `bool` is an `int` subclass, so the
  check must be explicit); outside the **inclusive** `[min, max]`; not in
  `options`. **Unknown keys are never rejected.**
  - Legacy origin: `app/services/component_type_service.py:240-271`
  - Definition of done: one test per rejection branch, one boundary test per
    bound (`min` and `max` accepted), one `bool`-for-`number` test, and one
    explicit test that an undeclared key is stored — the propeller mirror
    depends on that last behaviour.
  - Confidence: 🟢

- [ ] **T-05 — The 12 seeded types.**
  `DEFAULT_SEED_TYPES` with `deletable=False`: `material`, `servo`,
  `brushless_motor`, `battery`, `esc`, `propeller`, `receiver`, `spar_tube`,
  `veneer`, `strip`, `triangular_strip`, `grooved_strip`. Reproduce the property
  lists verbatim, **including** the German labels and
  `material.print_resolution_mm`.
  - Legacy origin: `app/services/component_type_service.py:331, 347`
  - Definition of done: the seeded `material` type declares both
    `density_kg_m3` and `print_resolution_mm` — the component tree's weight
    ladder reads them from a **material component's specs**, not from a tree
    node. Record the German labels as a gap rather than translating them.
  - Confidence: 🟢

- [ ] **T-06 — `seed_default_types` + `_patch_schema_fields`.**
  Idempotent insert-or-patch, called unconditionally at startup and by the test
  fixture. The patch is **additive only**: it adds properties declared in the
  seed and missing from the row, and never removes or rewrites an existing one.
  - Legacy origin: `app/services/component_type_service.py:682, 710`
  - Definition of done: two consecutive seeds leave exactly 12 rows; an operator
    edit to a seeded type's `label` survives a re-seed; adding a property to the
    seed list makes it appear on an existing row without a migration.
  - Confidence: 🟢

- [ ] **T-07 — Type CRUD with the guards.**
  `update_type` applies `label`, `description` and `schema` only — `name` and
  `deletable` are ignored, not rejected. `delete_type`: `deletable=False` → 409;
  referenced by ≥ 1 component → 409 with the count.
  - Legacy origin: `app/services/component_type_service.py`
  - Definition of done: a PUT changing `name` returns 200 with the old name; both
    409 paths are covered, and the referenced-type message contains the count.
  - Confidence: 🟢

- [ ] **T-08 — Component CRUD + the batch polar bridge.**
  `list_components(db, component_type, q)`; both writes call `validate_specs`;
  `_resolve_polar_id` collects the page's `model_ref`s and resolves them in
  **one** query; `ComponentRead` carries `has_polar` / `polar_id`.
  - Legacy origin: `app/services/component_service.py`
  - Definition of done: a query counter shows the statement count is independent
    of the row count; `has_polar` is true exactly when a polar shares the
    `model_ref`.
  - Confidence: 🟢

- [ ] **T-09 — `cots_import`.**
  Upsert on `(manufacturer, name)`; gate on `_VALID_COMPONENT_TYPES`; return
  `ImportResult{imported, updated, skipped, errors[]}`.
  - Legacy origin: `app/services/cots_import.py:26-40`
  - Definition of done: a re-import of an unchanged snapshot creates nothing; an
    unknown-type record lands in `errors` and the run continues. Reproduce the
    **second copy** of the taxonomy and record it as a gap rather than unifying
    it silently — the two lists are consumed at different times (startup vs CLI).
  - Confidence: 🟢

- [ ] **T-10 — Model upload / download.**
  `POST /components/{id}/model` stores the artefact and sets `model_ref`;
  `GET` returns it; a component with no model is a 404.
  - Legacy origin: `app/api/v2/endpoints/components.py:170-245`
  - Definition of done: upload → download round-trips the bytes; a missing model
    is 404. **Audit** the path handling against `.claude/rules/security.md`
    (`Path.resolve()` containment) before shipping — the legacy behaviour here
    was not verified.
  - Confidence: 🟡

- [ ] **T-11 — The two routers.**
  `/components` (7 routes, prefix on the router, tag `components`) and
  `/component-types` (5 routes, prefix on the router, tag `component-types`),
  with the `operation_id`s listed in [`../contracts.md`](../contracts.md) —
  including the legacy `GET /components/types` name list.
  - Legacy origin: `app/api/v2/endpoints/components.py:30`,
    `component_types.py:24`
  - Definition of done: contract tests per status code; `GET /components/types`
    still returns `{"types": [...]}` for backward compatibility.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — `validate_specs` matrix:** unknown type · missing required ·
      wrong type · `bool` for `number` · below `min` · above `max` · exactly
      `min` · exactly `max` · not in `options` · **unknown key accepted**.
- [ ] **TT-02 — Seeding:** 12 rows, all `deletable=false`, idempotent across two
      runs, operator label edit survives, new property patched in.
- [ ] **TT-03 — Type guards:** seeded delete 409 · referenced delete 409 with
      the count · `name`/`deletable` PUT silently ignored.
- [ ] **TT-04 — Component CRUD:** 201 / 200 / 200 / 204, unknown id 404.
- [ ] **TT-05 — Filters:** `component_type` exact match, `q` name search, and
      `total` matching the returned page.
- [ ] **TT-06 — Polar bridge:** `has_polar` true/false, and a query-count guard
      proving the batch resolution.
- [ ] **TT-07 — Nullable mass:** `mass_g = null` survives create, read and
      update; a test fails if it becomes `0`.
- [ ] **TT-08 — Import:** duplicate-free re-import · unknown type in `errors` ·
      the counts add up to the record count.
- [ ] **TT-09 — Offline guard:** the import CLI opens no socket.
- [ ] **TT-10 — Fast-tier guard:** neither service imports `aerosandbox` or
      `cadquery`.
- [ ] **TT-11 — Material specs contract:** a seeded `material` type declares
      `density_kg_m3` **and** `print_resolution_mm`, because the component
      tree's surface-print formula reads both from the material component
      (`component_tree_service.py:454`).

## Data Migration Tasks

- [ ] **TM-01 — Seed the registry** on an empty database (also runs at every
      startup, so this is a no-op on an existing one).
- [ ] **TM-02 — Import the non-propeller snapshots** (`dpower.json`,
      `generic_batteries.json`, `spektrum_avian.json`, `carbon_tubes.json`,
      `hoellein_wood.json`) via `scripts/import_cots.py`.
- [ ] **TM-03 — Patch existing types** with any properties added since the
      database was created — automatic via `_patch_schema_fields` on the next
      startup, no manual step.
- [ ] **TM-04 — Do NOT backfill `mass_g` with 0** for components whose mass is
      unknown; `NULL` is the correct value and the weight ladder depends on it.

## Suggested Order

1. **T-01 → T-03** — the two tables and the property schema. The `schema_def`
   mapping (T-02) is the single most consequential detail: getting it wrong
   fails at serialisation time, far from the cause.
2. **T-04** next, before any CRUD: it is a pure function over
   `(type schema, specs)` and is the use case's only integrity mechanism.
3. **T-05 → T-06** the seed data and the idempotent seeding, which every later
   test fixture depends on.
4. **T-07 → T-08** the two CRUD surfaces. T-08's batch resolution can be added
   after the naive version, guarded by the query-count test.
5. **T-09** ingestion, once CRUD and validation are stable.
6. **T-11** the routers, then **T-10** the model artefacts (peripheral, and the
   only task needing the artefact store).

## Pending Gaps (🔴)

- **Should the 12-type taxonomy live in one place** instead of
  `DEFAULT_SEED_TYPES` **and** `cots_import._VALID_COMPONENT_TYPES`?
- **Which upsert identity is canonical for `components`** —
  `(manufacturer, name)` or `(component_type, model_ref)`? Two importers use
  different keys against the same table.
- **Should `prop_component_seed` go through `validate_specs`**, so the mirror
  cannot write rows that violate the `propeller` schema?
- **Should `variant` (and any other key the mirror writes) be declared** in the
  `propeller` schema, so the schema becomes a complete contract?
- **Should the seeded labels be English?** They are German and rendered directly
  in the component editor.
- **Should the spec-key vocabulary be unified** (`c_rate` / `c_rating` /
  `discharge_c`; `continuous_current_a` / `max_continuous_a` /
  `max_current_a`)? Today a valid component can be invisible to one consumer.
- **Should deleting a *component* be guarded** when `component_tree` or
  `wing_xsec_ted_servos` still reference it?
- **Should an ignored `name` / `deletable` change be a 422** instead of a silent
  200?
- **Is the model-upload path traversal-safe?** Not verified in this analysis;
  `.claude/rules/security.md` requires an explicit containment check.
</content>
