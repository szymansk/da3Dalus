# aeroplane-core — Implementation Tasks

> Executable sequence to re-implement the module from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.

## Prerequisites

- [ ] Persistence layer available (SQLAlchemy 2.x, SQLite WAL or PostgreSQL) with
      the `get_db()` request-scoped session that **owns the transaction**
      (`app/db/session.py:55-64`, ADR 0009).
- [ ] `app/core/exceptions.py` hierarchy (`NotFoundError`, `ValidationError`,
      `ConflictError`, `InternalError`) and the global error-envelope handler.
- [ ] `branches` table available (module `versioning`) — `aeroplane-core` writes
      the first row of every lineage.
- [ ] `app/converters/model_schema_converters.py` available for the
      `AirplaneConfiguration` assembly.
- [ ] `ARTIFACTS_BASE_DIR` configured (used indirectly by the STEP cleanup on
      delete).

## Tasks

- [ ] **T-01 — `aeroplanes` table and `AeroplaneModel`.**
  Columns: `uuid` (GUID, unique, default `uuid4()`), `name`, `total_mass_kg`
  (nullable), `xyz_ref` (JSON, default `[0,0,0]`, metres),
  `assumption_computation_context` (JSON, nullable), `flight_profile_id` FK
  (indexed), `created_at` / `updated_at` (tz-aware, `onupdate=now()`), plus the
  versioning columns `branch_id`, `predecessor_id`, `root_id`, `is_immutable`
  (default false), `version_label`, `version_note`, `created_by`,
  `provenance_message_id`, `preview_png`. `branch_id`, `predecessor_id`,
  `root_id`, `provenance_message_id` must use `use_alter=True`.
  - Legacy origin: `app/models/aeroplanemodel.py:662`, data-dictionary
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
  add → `flush()` → `root_id = id` → create `main` branch
  (`head_id=id`, `is_main=True`, `created_by="human"`) → `flush()` →
  `branch_id = branch.id`. **No `commit()`.**
  - Legacy origin: `app/services/aeroplane_service.py:61, 75-100`
  - Definition of done: a created aeroplane satisfies `root_id == id`,
    `branch_id is not None`, and exactly one main branch exists for the lineage.
  - Confidence: 🟢

- [ ] **T-05 — `get_aeroplane_by_uuid` + `list_all_aeroplanes`.**
  Lookup by public UUID raising `NotFoundError(entity="Aeroplane",
  resource_id=uuid)`; listing ordered by `name`.
  - Legacy origin: `app/services/aeroplane_service.py:47, 106`
  - Definition of done: unknown UUID → 404 with the `not_found` envelope.
  - Confidence: 🟢

- [ ] **T-06 — `heads_only` projection on the list route.**
  Default `True`; restrict the result to nodes that are the `head_id` of some
  branch so immutable snapshots are hidden.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/base.py:76-95`
  - Definition of done: after `versioning` creates a snapshot, the default list
    is unchanged; `heads_only=false` shows both nodes.
  - Confidence: 🟢

- [ ] **T-07 — `get_aeroplane_schema` with eager materialisation.**
  Walk `wing.x_secs → detail → spares`, `detail.trailing_edge_device.servo_data`
  and the fuselages inside the session before building `AeroplaneSchema`.
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
  endpoint can answer 201 vs 200.
  - Legacy origin: `app/services/aeroplane_service.py:201, 218`;
    `base.py:200, 226`
  - Definition of done: first POST → 201, second POST → 200, stored value
    updated.
  - Confidence: 🟢

- [ ] **T-10 — `_to_json_compatible` NumPy stripper.**
  Recursively map `np.ndarray → list`, `np.generic → Python scalar`, recursing
  into dicts, lists and tuples.
  - Legacy origin: `app/services/aeroplane_service.py:33-44`
  - Definition of done: a payload containing `np.float64` and `np.ndarray`
    round-trips through `json.dumps` without error.
  - Confidence: 🟢

- [ ] **T-11 — `get_aeroplane_airplane_configuration` with the mass gate.**
  Raise `ValidationError` when `total_mass_kg is None` **before** any conversion;
  otherwise convert wings + fuselages through the converter hub and run
  `_to_json_compatible`.
  - Legacy origin: `app/services/aeroplane_service.py:252, 263-267`
  - Definition of done: mass-less aeroplane → 422; complete aeroplane → 200 with
    a JSON-serialisable body.
  - Confidence: 🟢

- [ ] **T-12 — `component_tree` table and `ComponentTreeNodeModel`.**
  `aeroplane_id` as an **indexed String** holding the aeroplane UUID (note: not
  an FK — see gap), `parent_id`, `sort_index`, `node_type`, `weight_override_g`,
  `component_id`, `quantity`, `construction_part_id`, `volume_mm3`, `area_mm2`,
  `material_id`, `print_type`, `print_resolution_mm`, `scale_factor`,
  `synced_from`.
  - Legacy origin: `app/models/component_tree.py:12-16`
  - Definition of done: nodes can be created for an aeroplane UUID and queried by
    it in one indexed lookup.
  - Confidence: 🟢

- [ ] **T-13 — `_calculate_own_weight` precedence chain.**
  `weight_override_g` → COTS `mass_g × quantity` → CAD-shape density formula →
  `(None, "none")`, with
  `surface: area_mm2 × print_resolution_mm × density_kg_m3 / 1e6 × scale_factor`
  and `volume: volume_mm3 × density_kg_m3 / 1e6 × scale_factor`,
  `print_resolution_mm` defaulting to **0.4**.
  - Legacy origin: `app/services/component_tree_service.py:432-474`
  - Definition of done: one unit test per branch of the chain, plus a test that
    an override beats a COTS mass.
  - Confidence: 🟢

- [ ] **T-14 — `_build_tree` (orphan-tolerant assembly).**
  Pass 1 builds `id → node`; pass 2 attaches to `parent_id`; a node whose parent
  is absent becomes a root. Sort children and roots by `sort_index`.
  - Legacy origin: `app/services/component_tree_service.py:58-79`
  - Definition of done: a node pointing at a deleted parent still appears, as a
    root, in the response.
  - Confidence: 🟢

- [ ] **T-15 — `_roll_up_weights` post-order traversal with the status ladder.**
  `total = own + Σ children`; status `valid` / `partial` / `invalid` per the rule
  in `design.md` §F4.
  - Legacy origin: `app/services/component_tree_service.py:82-120`
  - Definition of done: table-driven tests over leaf/all-valid/all-invalid/mixed
    combinations reproduce the exact status values.
  - Confidence: 🟢

- [ ] **T-16 — Pre-compute own weights before the recursion.**
  One dict built ahead of `_roll_up_weights` so the traversal issues no queries.
  - Legacy origin: `app/services/component_tree_service.py:133-137`
  - Definition of done: a tree of N nodes triggers a constant number of SQL
    statements, verified by a query counter.
  - Confidence: 🟢

- [ ] **T-17 — `_snapshot_construction_part_fields`.**
  Copy `volume_mm3` / `area_mm2` / `material_id` from the referenced construction
  part **only** for fields absent from `data.model_dump(exclude_unset=True)`.
  - Legacy origin: `app/services/component_tree_service.py:162-187`
  - Definition of done: an explicitly supplied `volume_mm3` survives the
    snapshot; an omitted one is filled from the part.
  - Confidence: 🟢

- [ ] **T-18 — `move_node` + `_is_descendant` cycle guard.**
  Reject a move whose new parent is a descendant of the moved node with
  `ValidationError` (→ 422).
  - Legacy origin: `app/services/component_tree_service.py:324-325, 339-359`
  - Definition of done: moving A under its own descendant B returns 422 and
    leaves the tree unchanged.
  - Confidence: 🟢

- [ ] **T-19 — `get_aircraft_total_weight_kg`.**
  Sum own + recursive children over all roots in grams, divide by 1000, and
  return **`None`** for an empty tree.
  - Legacy origin: `app/services/component_tree_service.py:381-403`
  - Definition of done: empty tree ⇒ `null`; a 350 g tree ⇒ `0.35`.
  - Confidence: 🟢

- [ ] **T-20 — `_sync_aircraft_mass` fire-and-forget.**
  Lazy-import `mass_cg_service.sync_component_tree_to_mass` inside the function
  (breaking the import cycle) and swallow every exception with a log line.
  - Legacy origin: `app/services/component_tree_service.py:362-378`
  - Definition of done: with the sync patched to raise, every tree CRUD route
    still returns its success status.
  - Confidence: 🟢

- [ ] **T-21 — Component-tree group auto-sync hooks.**
  Expose `sync_group_for_wing` / `sync_group_for_fuselage` and
  `delete_synced_nodes("<kind>:<name>")` for `wing_service` /
  `fuselage_service` to call.
  - Legacy origin: `wing_service.create_wing:298-300`,
    `fuselage_service.delete_fuselage:179-181` (gh#108)
  - Definition of done: creating a wing yields a group node with
    `synced_from = "wing:<name>"`; deleting the wing removes it.
  - Confidence: 🟢

- [ ] **T-22 — REST layer + `_raise_http_from_domain`.**
  Seven aggregate routes and six component-tree routes exactly as listed in
  [`contracts.md`](contracts.md), with the domain→HTTP mapping and a defensive
  `except Exception → 500` on every handler.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/base.py:52-67, 76-261`;
    `.../component_tree.py:52-128`
  - Definition of done: contract tests assert every status code in
    `contracts.md`, including 201-vs-200 on the mass upsert.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Happy path: create → read → export.** Create an aeroplane, add a
      wing and a fuselage, set the mass, fetch `airplane_configuration`, assert
      200 and JSON-serialisability (see `requirements.md` Acceptance Criteria).
- [ ] **TT-02 — Failure: export without mass returns 422** with
      `error.code == "validation_error"`.
- [ ] **TT-03 — Lineage invariant:** creating an aeroplane produces `root_id == id`
      and exactly one `is_main` branch; a second main branch insert raises at the
      DB level.
- [ ] **TT-04 — `heads_only` filter** hides an immutable snapshot by default and
      reveals it with `heads_only=false`.
- [ ] **TT-05 — Detached-instance guard:** serialise `AeroplaneSchema` after the
      session closes; the test must fail if the eager-materialisation walk is
      removed.
- [ ] **TT-06 — Weight roll-up matrix:** leaf valid/invalid, parent all-valid,
      all-invalid with and without own weight, mixed.
- [ ] **TT-07 — Own-weight precedence matrix:** override > cots > calculated >
      none, both print types, `print_resolution_mm` default 0.4.
- [ ] **TT-08 — Move-node cycle rejection** returns 422 and mutates nothing.
- [ ] **TT-09 — Empty tree weight is `null`**, not `0`.
- [ ] **TT-10 — Best-effort side effects:** patch STEP cleanup and mass sync to
      raise; delete and tree CRUD still succeed.
- [ ] **TT-11 — Construction-part snapshot** respects explicitly supplied fields.
- [ ] **TT-12 — Query-count guard** on the tree read (constant statements for N
      nodes).

## Data Migration Tasks

- [ ] **TM-01 — Backfill the versioning columns for pre-gh-903 rows.** Every legacy
      aeroplane needs `root_id = id`, an `is_main` branch and a `branch_id`;
      otherwise `heads_only=true` hides it. Reference migration:
      `alembic/versions/15f45e64a7c0_…` (see data-dictionary §versioning). 🟡
- [ ] **TM-02 — Reconcile orphaned `component_tree` rows.** Because
      `aeroplane_id` is not an FK, rows belonging to deleted aeroplanes may
      already exist; decide delete-vs-keep before enabling the new read path. 🔴

## Suggested Order

1. **T-01 → T-04** first: the model and the lineage bootstrap are the foundation
   everything else resolves against, and T-04 cannot be validated without T-03's
   partial index.
2. **T-05 → T-11** next: aggregate reads/writes and the export gate. T-07 depends
   on `wing-design` / `fuselage-design` models existing, so stub them if those
   modules are not yet implemented.
3. **T-12 → T-20** next: the component tree is independent of the aggregate
   routes except for the UUID lookup, so it can proceed in parallel with step 2.
   T-15 blocks on T-13; T-16 blocks on T-13; T-19 blocks on T-15.
4. **T-21** after both `wing-design` and `fuselage-design` exist (bidirectional
   dependency, broken by lazy imports).
5. **T-22** last — the REST layer is thin and only wires what is already tested.

## Pending Gaps (🔴)

- **Read-time cycle defence.** Should `_build_tree` / `_roll_up_weights` gain a
  depth limit or explicit cycle detection, or is the `move_node` write guard the
  intended level of protection?
- **`component_tree.aeroplane_id` as a plain String.** Should it become an FK to
  `aeroplanes.uuid` with `ON DELETE CASCADE`, and is orphan cleanup handled
  elsewhere today?
- **Dead legacy router `app/api/v2/endpoints/aeroplane.py`.** Delete or retain?
- **`SQLALCHEMY_DATABASE_URL` read with bare `os.getenv`** instead of through
  `app/core/config.py` — intentional bootstrap exception or oversight?
- **German user-facing messages** from the `IntegrityError` and
  `RequestValidationError` handlers in an otherwise English API.
