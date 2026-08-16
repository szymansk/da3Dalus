# versioning — Implementation Tasks

> Executable sequence to re-implement the module from the legacy behaviour.
> Every task cites the legacy file, a definition of done, and a confidence
> marker.
> Use-case task lists: [`branch-model`](branch-model/tasks.md) ·
> [`snapshot-immutability`](snapshot-immutability/tasks.md) ·
> [`aeroplane-clone-subgraph`](aeroplane-clone-subgraph/tasks.md) ·
> [`copilot-provenance`](copilot-provenance/tasks.md).

## Prerequisites

- [ ] `aeroplanes` table and `AeroplaneModel` with every owned relationship
      (wings, fuselages, weight items, assumptions, stability results, loading
      scenarios, mission objective, computation config).
- [ ] `component_tree` table, addressed by a **string** `aeroplane_id` holding
      the aeroplane UUID — module `aeroplane-core`.
- [ ] `get_db()` request-scoped session owning the transaction
      (`app/db/session.py:55-64`, ADR 0009). Nothing here may commit.
- [ ] `app/core/exceptions.py` with `NotFoundError`, `ValidationError`,
      `ConflictError`, `ServiceException`.
- [ ] Alembic configured with **batch mode** for SQLite (the nine columns are
      added to an existing table).
- [ ] A database that supports **partial** unique indexes — SQLite (`WHERE
      is_main = 1`) and PostgreSQL (`WHERE is_main = true`) are both targeted.

## Tasks

- [ ] **T-01 — `branches` table + the partial unique index.**
  `root_id` and `head_id` (Integer FKs → `aeroplanes.id`, both `use_alter=True`
  with explicit constraint names), `name`, `is_main` (Boolean,
  `server_default="false"`), `created_by`, `created_at`. Index
  `uq_branches_one_main_per_root ON branches(root_id)` with
  `sqlite_where=text("is_main = 1")` and
  `postgresql_where=text("is_main = true")`.
  - Legacy origin: `app/models/aeroplanemodel.py:602-660`
  - Definition of done: the index is declared **identically** in the model and
    the migration, so `create_all` (tests) and a migrated database agree — a
    test asserts a second `is_main` insert for the same `root_id` raises an
    `IntegrityError` on **both** backends.
  - Confidence: 🟢

- [ ] **T-02 — The nine versioning columns on `aeroplanes`.**
  `branch_id`, `predecessor_id`, `root_id` (all `use_alter=True` FKs),
  `is_immutable` (NOT NULL, `server_default="false"`), `version_label`,
  `version_note`, `created_by`, `provenance_message_id` (FK →
  `copilot_messages.id`), `preview_png`. Relationships disambiguated with
  explicit `foreign_keys=`.
  - Legacy origin: `app/models/aeroplanemodel.py:662-716`
  - Definition of done: the circular FK pair
    (`aeroplanes.branch_id ↔ branches.root_id/head_id`) is emitted as separate
    `ALTER TABLE` statements and `create_all` succeeds.
  - Confidence: 🟢

- [ ] **T-03 — The gh-903 migration.**
  Create `branches`; add the nine columns and four FK constraints in **batch**
  mode; backfill one `main` branch per existing aeroplane using
  `INSERT … RETURNING id` (**not** `lastrowid`, which is `None` on PostgreSQL)
  and then `UPDATE aeroplanes SET root_id = self, branch_id = <new>,
  is_immutable = 0`; create the partial index; **`DROP TABLE
  design_versions`**. The downgrade recreates `design_versions` **empty**.
  - Legacy origin: `alembic/versions/15f45e64a7c0_gh903_versioning_db_model.py`
  - Definition of done: a database with N pre-existing aeroplanes ends with N
    main branches and no `branch_id IS NULL` row; the migration runs on both
    backends.
  - Confidence: 🟢

- [ ] **T-04 — The resolution helpers and the immutability guard.**
  `_get_node`, `_get_branch` (both raising `NotFoundError` with the id in
  `details`), `_guard_immutable` (raising `ValidationError` with `node_id` and
  `is_immutable`).
  - Legacy origin: `app/services/aeroplane_version_service.py:41-71`
  - Definition of done: each raises with the documented message.
    `_get_node_by_uuid` may be implemented for symmetry but **must** be recorded
    as having no caller — the whole API is integer-PK.
  - Confidence: 🟢

- [ ] **T-05 — `_metrics_payload`.**
  `id`, `uuid`, `name`, `total_mass_kg`; `assumption_computation_context`
  **only when non-empty**; `wing_count`, `wing_names[]`, `wings[{name,
  n_xsecs}]`, `fuselage_count`; `stability` from `stability_results[-1]` when
  present.
  - Legacy origin: `app/services/aeroplane_version_service.py:74-117`
  - Definition of done: `wing_names` and `n_xsecs` are present (gh-938 — the
    copilot targets wings by name and appends at `at_index = n_xsecs`); a node
    with an empty context omits the key entirely. Record that `[-1]` is
    insertion order, not `computed_at` order.
  - Confidence: 🟢

- [ ] **T-06 — `snapshot`.**
  Guard immutability; `resolved_root_id = head.root_id or head.id`; clone with
  `immutable=True`, `branch_id=head.branch_id`,
  `predecessor_id=head.predecessor_id`; set label / note /
  `provenance_message_id` / `created_by="human"`; flush; re-point
  `head.predecessor_id = snapshot.id`; flush.
  - Legacy origin: `app/services/aeroplane_version_service.py:125-183`
  - Definition of done: the head keeps its id **and uuid**; the snapshot
    inherits the head's *old* predecessor; a snapshot of the lineage root gets
    the root's id as `root_id`. Reproduce the hard-coded `"human"` and record it
    as a gap.
  - Confidence: 🟢

- [ ] **T-07 — `create_branch`.**
  `root_id = source.root_id or source.id`; clone with `immutable=False`,
  `branch_id=None`, `predecessor_id=source.id`; set `created_by`; flush; create
  the `BranchModel` with `is_main=False`; flush; back-fill
  `new_head.branch_id`; flush.
  - Legacy origin: `app/services/aeroplane_version_service.py:186-241`
  - Definition of done: the three-flush order is preserved (the circular FK pair
    cannot be satisfied in one statement); the source may be a head **or** a
    snapshot. Reproduce the **absence** of a name-collision check and record it.
  - Confidence: 🟢

- [ ] **T-08 — `adopt_branch` with demote-first.**
  Already-main ⇒ `ConflictError`; find the lineage's current main, set
  `is_main = False`, **flush**, then promote and flush.
  - Legacy origin: `app/services/aeroplane_version_service.py:244-288`
  - Definition of done: a test that swaps the two statements must fail with an
    `IntegrityError` from the partial index — this is the proof the order is
    load-bearing. A lineage with no current main still promotes.
  - Confidence: 🟢

- [ ] **T-09 — `restore`.**
  Require `is_immutable=True` (else `ValidationError`); default the name to
  `restore/<version_label or node_id>`; delegate to `create_branch`.
  - Legacy origin: `app/services/aeroplane_version_service.py:291-321`
  - Definition of done: restoring from a mutable head is 422; the default name
    covers both the labelled and unlabelled cases.
  - Confidence: 🟢

- [ ] **T-10 — `discard_branch` with its five-step order.**
  Guards (main → 409, only branch → 409); collect nodes by `branch_id`; null
  inbound `predecessor_id`s with `synchronize_session="fetch"`; **delete the
  branch row first**; then delete each node.
  - Legacy origin: `app/services/aeroplane_version_service.py:324-393`
  - Definition of done: three tests prove the order matters — deleting the nodes
    first violates `branches.head_id NOT NULL`; skipping the predecessor nulling
    violates the FK on SQLite; both guards return 409. A surviving node keeps
    existing with `predecessor_id = null`.
  - Confidence: 🟢

- [ ] **T-11 — `rename_branch`.**
  Strip; empty ⇒ `ValidationError`; a same-`root_id` name on a **different**
  branch ⇒ `ConflictError` with both ids in `details`.
  - Legacy origin: `app/services/aeroplane_version_service.py:459-512`
  - Definition of done: renaming a branch to its **own** current name succeeds
    (the query excludes `id == branch_id`); `"   "` is 422.
  - Confidence: 🟢

- [ ] **T-12 — `list_tree` and `compare`.**
  `list_tree`: confirm the root exists, then `id == root_id OR root_id ==
  root_id` ordered by `id`, plus the lineage's branches ordered by `id`.
  `compare`: two `_get_node` calls and two payloads, read-only.
  - Legacy origin: `app/services/aeroplane_version_service.py:396-456`
  - Definition of done: a node with a `NULL` `root_id` is **absent** from the
    tree (reproduce, then record the gap); `compare` does not require a shared
    lineage.
  - Confidence: 🟢

- [ ] **T-13 — `list_aeroplanes_heads_only`.**
  `branch_id IS NULL` **OR** `id IN (SELECT head_id FROM branches)`, ordered by
  `name`.
  - Legacy origin: `app/services/aeroplane_version_service.py:515-534`
  - Definition of done: a legacy row with no branch is listed; an immutable
    snapshot is not.
  - Confidence: 🟢

- [ ] **T-14 — `CLONED_TABLES` / `EXCLUDED_TABLES` + the coverage test.**
  17 cloned, 18 excluded with a **mandatory non-empty reason** each; the test
  discovers related tables by introspecting SQLAlchemy `ForeignKey` objects and
  asserts every discovered table is in exactly one set, and that the sets are
  disjoint.
  - Legacy origin: `app/services/aeroplane_clone_service.py:70-132`,
    `app/tests/test_aeroplane_clone_coverage.py`
  - Definition of done: adding a new FK-bearing table makes the test fail until
    it is registered. Carry the **blind-spot comment** verbatim: string-FK
    tables (`component_tree`, `construction_plans`, `construction_parts`) are
    invisible to the BFS and must be maintained by hand.
  - Confidence: 🟢

- [ ] **T-15 — `clone_aeroplane_subgraph` — the ten groups.**
  In order, with a `flush()` after each so PKs are available for re-keying;
  new `uuid4`; deep-copy `xyz_ref` and `assumption_computation_context`; keep
  `flight_profile_id`; null the five version-metadata columns.
  - Legacy origin: `app/services/aeroplane_clone_service.py:140-455`
  - Definition of done: every one of the 17 tables has new rows with new PKs and
    no row object is shared with the source. See
    [`aeroplane-clone-subgraph/tasks.md`](aeroplane-clone-subgraph/tasks.md) for
    the per-group detail.
  - Confidence: 🟢

- [ ] **T-16 — `_remap_component_overrides`.**
  Walk `toggles`, `mass_overrides` and `position_overrides`; rewrite each
  `component_uuid` through `weight_id_map`; values **not** in the map pass
  through unchanged (they are COTS UUIDs).
  - Legacy origin: `app/services/aeroplane_clone_service.py:463-491`
  - Definition of done: a scenario referencing weight item `"7"` points at the
    clone's copy; a COTS UUID is untouched; `None` / empty overrides are
    deep-copied without error.
  - Confidence: 🟢

- [ ] **T-17 — `_clone_component_tree` — two passes.**
  Pass 1 inserts every node with `parent_id=None`, flushing per node to collect
  `old_id → new_id`; pass 2 issues an `UPDATE` per node to restore the parent.
  An unmappable parent leaves `parent_id = None` **and logs a warning naming
  both ids**.
  - Legacy origin: `app/services/aeroplane_clone_service.py:494-580`
  - Definition of done: the cloned tree has the same shape; `aeroplane_id` is
    `str(clone.uuid)`; the shared references (`component_id`,
    `construction_part_id`, `material_id`) are unchanged; the warning path is
    covered. **Note:** the legacy copy list omits no column that exists today —
    verify field-by-field against the model before shipping, because a silently
    dropped column would lose data on every version.
  - Confidence: 🟢

- [ ] **T-18 — The eight routes.**
  Exactly as in [`contracts.md`](contracts.md), all **integer-PK** addressed,
  with `_raise_http` / `_call` and the `_node_to_schema` / `_branch_to_schema`
  mappers; `is_head` computed at the endpoint from `{b.head_id}`.
  - Legacy origin: `app/api/v2/endpoints/versioning.py`
  - Definition of done: contract tests per status code, including 201 on
    snapshot / branch / restore, 204 on discard, and 409 on adopt-main,
    discard-main and discard-only.
  - Confidence: 🟢

- [ ] **T-19 — Wire the two automated callers.**
  `spar_insert_service` takes an automatic immutable snapshot labelled
  `"Before spar insert"` **before** any destructive mutation and **aborts the
  whole commit if the snapshot fails**, returning the snapshot id in
  `SparInsertResponse`. `copilot_apply_service` opens and discards the
  `copilot-proposal` branch.
  - Legacy origin: `app/services/spar_insert_service.py:485-497` (gh-1058),
    `app/services/copilot_apply_service.py:107-241`
  - Definition of done: with `snapshot` patched to raise, the spar commit
    performs **no** mutation — the abort is the point of BR-41.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Partial index:** two `is_main` rows for one `root_id` raise, on
      both SQLite and PostgreSQL.
- [ ] **TT-02 — Migration:** N legacy aeroplanes ⇒ N main branches, no
      `branch_id IS NULL`, `design_versions` dropped.
- [ ] **TT-03 — Snapshot topology:** `S.predecessor_id == old P`,
      `H.predecessor_id == S`, `H.id` and `H.uuid` unchanged.
- [ ] **TT-04 — Snapshot guards:** immutable node ⇒ 422; root snapshot resolves
      `root_id`.
- [ ] **TT-05 — Branch creation:** from a head and from a snapshot; `branch_id`
      back-filled; `is_main` false.
- [ ] **TT-06 — Adopt:** promotion + demotion; exactly one `is_main` after;
      already-main ⇒ 409; **order-swap test must fail**.
- [ ] **TT-07 — Restore:** mutable ⇒ 422; default names for labelled and
      unlabelled snapshots.
- [ ] **TT-08 — Discard:** both 409 guards; the branch-first delete order;
      inbound predecessors nulled; the subgraph cascades.
- [ ] **TT-09 — Rename:** strip; empty ⇒ 422; collision ⇒ 409; renaming to its
      own name succeeds.
- [ ] **TT-10 — Tree:** nodes and branches ordered by id; `is_head` correct;
      a `NULL`-`root_id` node absent (characterisation).
- [ ] **TT-11 — Heads-only listing:** legacy rows visible, snapshots hidden.
- [ ] **TT-12 — Clone coverage:** the registry test; adding a new FK table
      fails until registered; every exclusion reason is non-empty.
- [ ] **TT-13 — Clone fidelity:** all 17 tables copied with new PKs; no shared
      row; new `uuid4`; STEP paths and version metadata nulled.
- [ ] **TT-14 — Shared references preserved:** `flight_profile_id`,
      `servo.component_id`, `component_tree.component_id` /
      `construction_part_id` / `material_id`.
- [ ] **TT-15 — Override remapping:** weight-item ids re-keyed, COTS UUIDs
      untouched.
- [ ] **TT-16 — Component-tree parentage:** shape preserved; unmappable parent
      ⇒ `null` + a warning naming both ids.
- [ ] **TT-17 — No commit:** a rollback after any operation leaves nothing
      persisted.
- [ ] **TT-18 — `_metrics_payload`:** `wing_names`, `n_xsecs`, the omitted
      empty context, `stability` from the last row.
- [ ] **TT-19 — Spar-insert abort:** `snapshot` patched to raise ⇒ no mutation
      is performed (BR-41).
- [ ] **TT-20 — Provenance:** a copilot branch carries `"copilot"`; a REST
      branch defaults to `"human"`; a snapshot is always `"human"`
      (characterisation).
- [ ] **TT-21 — Error envelope:** every 4xx/5xx body is `{"detail": …}`, never
      `{"error": {…}}`.

## Data Migration Tasks

- [ ] **TM-01 — Create `branches` and add the nine columns** (batch mode on
      SQLite).
- [ ] **TM-02 — Backfill one `main` branch per existing aeroplane** with
      `INSERT … RETURNING id`; then set `root_id = self`, `branch_id = <new>`,
      `is_immutable = 0`. **Never** use `lastrowid` — it is `None` on
      PostgreSQL and would leave every `branch_id` NULL.
- [ ] **TM-03 — Create the partial unique index** after the backfill, so the
      backfill cannot violate it mid-flight.
- [ ] **TM-04 — Drop `design_versions`.** The downgrade recreates it **empty**;
      snapshots were never back-migrated, so a downgrade is lossy. Say so in
      the migration docstring.
- [ ] **TM-05 — Leave legacy `branch_id IS NULL` rows visible.** If any survive
      the backfill, `list_aeroplanes_heads_only` must still return them.

## Suggested Order

1. **T-01 → T-03** — the schema and the migration first. The partial index and
   the circular FK pair shape every later decision, and the backfill is the only
   step that touches existing production data.
2. **T-04 → T-05** the helpers and `_metrics_payload`: small, pure, and used by
   almost everything below (including two other modules).
3. **T-14 → T-17** the **clone engine before the operations**. Snapshot, branch
   and restore are all thin wrappers over it, so a partially correct clone would
   make every operation test ambiguous. The coverage registry (T-14) comes
   first: it is what tells you which tables T-15 must handle.
4. **T-06 → T-07** snapshot and branch, in that order — snapshot exercises the
   clone with `immutable=True` and no branch row, which is the simpler case.
5. **T-08 → T-11** adopt, restore, discard, rename. T-08 and T-10 carry the two
   ordering constraints and deserve dedicated failure tests.
6. **T-12 → T-13** the read paths, which need a populated lineage to be
   meaningful.
7. **T-18** the routes, then **T-19** the two automated callers — `spar_insert`
   last, because its abort semantics only make sense once `snapshot` is proven.

## Pending Gaps

- **Is there a retention policy for snapshots?** Every snapshot is a full
  subgraph copy, `spar_insert_service` snapshots automatically on every
  destructive commit, and nothing prunes, counts or measures them.
- **Should `discard_branch` refuse to delete a node another node still descends
  from**, instead of nulling the link and truncating the survivor's lineage?
- **Should `list_tree` find nodes with a `NULL` `root_id`?** They exist and are
  invisible in the version graph.
- **Should `create_branch` check for a name collision**, as `rename_branch`
  does — or should the DB carry a `(root_id, name)` unique constraint?
- **What is the `created_by` vocabulary?** Four writers produce `'human'`,
  `'ai'` (documented, never written) and `'copilot'`; there is no enum.
- **Should `provenance_message_id` be readable?** Nothing resolves a snapshot
  back to the conversation turn that produced it.
- **Should `preview_png` be generated**, or should the column be dropped?
- **Should the versioning routes accept UUIDs** like the rest of v2?
  `_get_node_by_uuid` already exists and is dead.
- **Should `compare` perform a server-side diff**, and should it require both
  nodes to share a lineage?
- **Should `_metrics_payload` order `stability_results` by `computed_at`**
  instead of taking the last inserted row?
- **What should the `design-versions` routes return** — 410 Gone, 501, or should
  they be unmounted?
- **How is the clone coverage blind spot closed** for tables whose aeroplane
  reference is a plain `String`?
</content>
