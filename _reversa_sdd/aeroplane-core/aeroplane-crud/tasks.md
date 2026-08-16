# aeroplane-crud — Implementation Tasks

> Executable sequence to re-implement the use case from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
> Parent module tasks: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] Persistence layer available (SQLAlchemy 2.x, SQLite WAL or PostgreSQL) with
      the `get_db()` request-scoped session that **owns the transaction**
      (`app/db/session.py:55-64`, ADR 0009).
- [ ] `app/core/exceptions.py` hierarchy (`NotFoundError`, `ValidationError`,
      `ConflictError`, `InternalError`) and the global error-envelope handler.
- [ ] `branches` table available (module `versioning`) — this use case writes the
      first row of every lineage and cannot be validated without it.
- [ ] `wings` / `fuselages` models available (modules `wing-design`,
      `fuselage-design`) for the nested read model; stub them if those modules do
      not exist yet.
- [ ] `ARTIFACTS_BASE_DIR` configured — used indirectly by the STEP cleanup on
      delete.

## Tasks

- [ ] **T-01 — `aeroplanes` table and `AeroplaneModel`.**
  Columns: `uuid` (GUID, unique, default `uuid4()`), `name`, `total_mass_kg`
  (nullable), `xyz_ref` (JSON, default `[0,0,0]`, metres),
  `assumption_computation_context` (JSON, nullable), `flight_profile_id` FK
  (indexed), `created_at` / `updated_at` (tz-aware, `onupdate=now()`), plus the
  versioning columns `branch_id`, `predecessor_id`, `root_id`, `is_immutable`
  (default false), `version_label`, `version_note`, `created_by`,
  `provenance_message_id`, `preview_png`. `branch_id`, `predecessor_id`,
  `root_id` and `provenance_message_id` must use `use_alter=True`.
  - Legacy origin: `app/models/aeroplanemodel.py:662`; data-dictionary
    §Table `aeroplanes`
  - Definition of done: the DDL emits the circular FKs as separate `ALTER TABLE`
    statements and the table creates cleanly on a fresh database.
  - Confidence: 🟢

- [ ] **T-02 — Cascading relationships.**
  `wings`, `fuselages`, `weight_items`, `copilot_messages`, `design_assumptions`,
  `computation_config` (1:1), `stability_results`, `loading_scenarios`,
  `mission_objective` (1:1) all with `cascade="all, delete-orphan"`;
  `flight_profile` many-to-one **without** cascade.
  - Legacy origin: `app/models/aeroplanemodel.py:718-795`
  - Definition of done: deleting an aeroplane removes every child row in one
    flush and leaves the shared `rc_flight_profiles` row intact.
  - Confidence: 🟢

- [ ] **T-03 — Partial unique index for the main branch.**
  `uq_branches_one_main_per_root` over `(root_id)` `WHERE is_main`.
  - Legacy origin: `app/models/aeroplanemodel.py:616-624`
  - Definition of done: an attempt to insert a second `is_main` branch for the
    same `root_id` raises an `IntegrityError` at the database level.
  - Confidence: 🟢

- [ ] **T-04 — `create_aeroplane` lineage bootstrap.**
  `db.add()` → `flush()` → `root_id = id` → create the `main` branch
  (`root_id=id`, `head_id=id`, `is_main=True`, `created_by="human"`) →
  `flush()` → `branch_id = branch.id`. **No `commit()`.**
  - Legacy origin: `app/services/aeroplane_service.py:61, 75-100`
  - Definition of done: a created aeroplane satisfies `root_id == id`,
    `branch_id is not None`, and exactly one main branch exists for the lineage.
  - Confidence: 🟢

- [ ] **T-05 — `get_aeroplane_by_uuid` + `list_all_aeroplanes`.**
  Lookup by public UUID raising `NotFoundError(entity="Aeroplane",
  resource_id=uuid)`; listing ordered by `name`.
  - Legacy origin: `app/services/aeroplane_service.py:47, 106`
  - Definition of done: unknown UUID → 404 with the `not_found` envelope; the
    list is name-ordered.
  - Confidence: 🟢

- [ ] **T-06 — `heads_only` projection on the list route.**
  Default `True`; restrict the result to nodes that are the `head_id` of some
  branch so immutable snapshots are hidden.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/base.py:76-95`
  - Definition of done: after `versioning` creates a snapshot, the default list
    is unchanged; `heads_only=false` shows both nodes.
  - Confidence: 🟢

- [ ] **T-07 — `get_aeroplane_schema` with eager materialisation.**
  Walk `wing.x_secs → detail → spares`,
  `detail.trailing_edge_device.servo_data` and the fuselages **inside the
  session** before building `AeroplaneSchema.model_validate(aeroplane)`.
  - Legacy origin: `app/services/aeroplane_service.py:129, 141-149`
  - Definition of done: an integration test that serialises the response **after**
    session close passes without `DetachedInstanceError`; removing the walk makes
    it fail (guard test).
  - Confidence: 🟢

- [ ] **T-08 — `delete_aeroplane` with best-effort artefact cleanup.**
  ORM delete, then `cleanup_aeroplane_step_files()` inside a bare `try/except`
  that logs only.
  - Legacy origin: `app/services/aeroplane_service.py:169, 191-198`
  - Definition of done: with the cleanup function patched to raise, the delete
    still returns 200 and the rows are gone.
  - Confidence: 🟢

- [ ] **T-09 — `get_aeroplane_mass` / `set_aeroplane_mass` upsert.**
  `set_aeroplane_mass` returns `True` when the value was newly created so the
  endpoint can answer **201** vs **200**. Unit: kilograms.
  - Legacy origin: `app/services/aeroplane_service.py:201, 218`;
    `base.py:200, 226`
  - Definition of done: first POST → 201, second POST → 200, stored value
    updated; unknown UUID → 404 on both routes.
  - Confidence: 🟢

- [ ] **T-10 — `_raise_http_from_domain` and the six routes.**
  Map `NotFoundError → 404 not_found`, `ValidationError → 422
  validation_error`, `ConflictError → 409 conflict`, `InternalError → 500
  internal_error`, bare `ServiceException → 500 service_error`; every handler
  additionally carries a defensive `except Exception → 500`. Wire the six routes
  exactly as listed in [`design.md`](design.md) §Interface.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/base.py:52-67, 76-250`
  - Definition of done: contract tests assert every status code, including
    201-vs-200 on the mass upsert and the uniform `{"error": {...}}` envelope.
  - Confidence: 🟢

- [ ] **T-11 — Decide the `IntegrityError` handler's contract.**
  Today it maps every integrity violation to **409** with the German message
  `"name existiert bereits"` although `aeroplanes.name` has no unique
  constraint. Replace with an English message and a constraint-aware mapping, or
  document the current behaviour deliberately.
  - Legacy origin: `app/main.py` global exception handlers (see
    [`../contracts.md`](../contracts.md) §Global error contract)
  - Definition of done: the chosen behaviour is covered by a test that asserts
    the emitted `code` and `message` for a real constraint violation.
  - Confidence: 🟢 — decided: translate all German strings to English (`Q-CC-5`)
    and remove the misreporting handler from the aeroplane path (`Q-AC-2`).

## Test Tasks

- [ ] **TT-01 — Happy path: create → read → delete.** Create an aeroplane, add a
      wing and a fuselage, read the nested schema, delete, assert every child row
      is gone (see [`requirements.md`](requirements.md) Acceptance Criteria).
- [ ] **TT-02 — Failure: unknown UUID returns 404** with
      `error.code == "not_found"` on read, delete, mass-read and mass-write.
- [ ] **TT-03 — Lineage invariant:** creating an aeroplane produces `root_id ==
      id`, `branch_id is not None` and exactly one `is_main` branch; a second
      main-branch insert raises at the DB level (guards T-03 and T-04 together).
- [ ] **TT-04 — `heads_only` filter** hides an immutable snapshot by default and
      reveals it with `heads_only=false`.
- [ ] **TT-05 — Detached-instance guard:** serialise `AeroplaneSchema` after the
      session closes; the test must fail if the eager-materialisation walk of
      T-07 is removed.
- [ ] **TT-06 — Mass upsert status codes:** first POST → 201, second → 200,
      stored value updated.
- [ ] **TT-07 — Best-effort cleanup:** patch `cleanup_aeroplane_step_files` to
      raise; the delete still returns 200 and logs the failure.
- [ ] **TT-08 — Cascade completeness:** a delete removes wings, fuselages, weight
      items, assumptions, copilot messages, loading scenarios and stability
      results, and leaves the shared `rc_flight_profiles` row intact.
- [ ] **TT-09 — Name ordering** on the list route, including case handling
      (record whatever the implementation does — the legacy behaviour is a plain
      `ORDER BY name`). 🟡

## Data Migration Tasks

- [ ] **TM-01 — Backfill the versioning columns for pre-gh-903 rows.** Every
      legacy aeroplane needs `root_id = id`, an `is_main` branch and a
      `branch_id`; otherwise `heads_only=true` hides it from the default list.
      Reference migration: `alembic/versions/15f45e64a7c0_…` (see data-dictionary
      §versioning). 🟡

## Suggested Order

1. **T-01 → T-04** first: the model, the cascade and the partial index are the
   foundation. T-04 cannot be validated without T-03's index, so they land
   together.
2. **T-05, T-06** next: the lookup and the list projection. T-06 needs the
   `branches` table from `versioning` to be meaningful.
3. **T-07** after `wing-design` / `fuselage-design` models exist (or against
   stubs) — the materialisation walk has nothing to walk otherwise.
4. **T-08, T-09** are independent of one another and of T-07; both only need
   T-05.
5. **T-10** last — the REST layer is thin and only wires what is already tested.
6. **T-11** is a decision, not a dependency; it can land at any point once the
   product question in Pending Gaps is answered.

## Resolved by the validation interview (2026-08-15)

- 🟢 **German user-facing messages** — all translated to English (`Q-CC-5`,
  maintainer-answered). Covers `"name existiert bereits"` → 409 and
  `"Ungültige Eingabedaten"` → 422.
- 🟢 **`aeroplanes.name` stays non-unique** (`Q-AC-2`, maintainer-confirmed) and
  the misreporting `IntegrityError` handler is removed from the aeroplane path.
- 🟡 **Dead legacy router `app/api/v2/endpoints/aeroplane.py`** — delete, per
  `P-DEAD-0` rule 3 (`Q-CC-6`). Derived from policy, not decided by the
  maintainer, so INFERRED until executed.
- 🟡 **`SQLALCHEMY_DATABASE_URL`** folds into the merged settings class
  (`Q-CC-4`), unless Alembic provably needs it before settings can be
  constructed — in which case it is documented as a deliberate bootstrap
  exception. To be verified during implementation.

## Pending Gaps (🔴)
- **Delete does not reach `component_tree`** because `aeroplane_id` is a plain
  String rather than an FK. Should the delete path explicitly remove tree rows?
  Tracked in [`../component-tree/tasks.md`](../component-tree/tasks.md).
