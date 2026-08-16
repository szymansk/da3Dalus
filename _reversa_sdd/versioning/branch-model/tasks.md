# branch-model — Implementation Tasks

> Executable sequence to re-implement the use case from the legacy behaviour.
> Every task cites the legacy file, a definition of done, and a confidence
> marker. Parent module tasks: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] `aeroplanes` table with the four versioning columns — see
      [`../tasks.md`](../tasks.md) T-02.
- [ ] `clone_aeroplane_subgraph` available — see
      [`../aeroplane-clone-subgraph/tasks.md`](../aeroplane-clone-subgraph/tasks.md).
      `create_branch` is a clone plus two rows; it cannot be built without it.
- [ ] `get_db()` request-scoped session (ADR 0009). Nothing here commits.
- [ ] `app/core/exceptions.py` with `NotFoundError`, `ValidationError`,
      `ConflictError`.
- [ ] A database supporting **partial** unique indexes: SQLite (`WHERE
      is_main = 1`) and PostgreSQL (`WHERE is_main = true`).

## Tasks

- [ ] **T-01 — `branches` table.**
  `root_id` / `head_id` (Integer FKs → `aeroplanes.id`, both `use_alter=True`
  with explicit constraint names `fk_branches_root_id` / `fk_branches_head_id`),
  `name`, `is_main` (Boolean, `server_default="false"`), `created_by`,
  `created_at` (`func.now()`). Relationships `root` / `head` with explicit
  `foreign_keys=`.
  - Legacy origin: `app/models/aeroplanemodel.py:602-660`
  - Definition of done: `create_all` succeeds despite the circular FK pair; both
    relationships resolve without an ambiguity error.
  - Confidence: 🟢

- [ ] **T-02 — The partial unique index.**
  `Index("uq_branches_one_main_per_root", "root_id", unique=True,
  sqlite_where=text("is_main = 1"), postgresql_where=text("is_main = true"))` —
  declared **identically** in the model and the migration.
  - Legacy origin: `app/models/aeroplanemodel.py:616-624` + the migration
  - Definition of done: inserting a second `is_main=true` row for one `root_id`
    raises an `IntegrityError` on **both** backends; a second `is_main=false`
    row is fine. A test asserts the model-declared and migration-declared index
    definitions match.
  - Confidence: 🟢

- [ ] **T-03 — `create_branch` with the three-flush dance.**
  `root_id = source.root_id or source.id`; clone with `immutable=False`,
  `branch_id=None`, `predecessor_id=source.id`; set `created_by`; **flush**;
  insert `BranchModel(is_main=False)`; **flush**; back-fill
  `new_head.branch_id`; **flush**. `logger.info` with source, branch, head and
  name.
  - Legacy origin: `app/services/aeroplane_version_service.py:186-241`
  - Definition of done: the head's `branch_id` is populated; the source may be
    a mutable head **or** an immutable snapshot (no guard); a test collapsing
    the flushes must fail. Reproduce the **absence** of a name-collision check
    and record it as a gap.
  - Confidence: 🟢

- [ ] **T-04 — `adopt_branch` with demote-first.**
  Already-main ⇒ `ConflictError`; select the lineage's current main; set
  `is_main = False`; **flush**; then promote and flush. Tolerate
  `current_main is None`.
  - Legacy origin: `app/services/aeroplane_version_service.py:244-288`
  - Definition of done: exactly one `is_main` remains; a deliberately
    order-swapped variant raises `IntegrityError` (this test is the proof the
    order is load-bearing); a lineage with no main still promotes.
  - Confidence: 🟢

- [ ] **T-05 — `rename_branch`.**
  Strip; empty ⇒ `ValidationError("Branch name must not be empty")`; conflict
  query on `root_id == branch.root_id AND name == stripped AND id != branch_id`
  ⇒ `ConflictError` with `branch_id`, `conflicting_branch_id` and `name` in
  `details`.
  - Legacy origin: `app/services/aeroplane_version_service.py:459-512`
  - Definition of done: `"  tidy  "` stores `"tidy"`; `"   "` is 422; a
    collision is 409; renaming a branch to its **own** name succeeds (the
    `id != branch_id` clause).
  - Confidence: 🟢

- [ ] **T-06 — `discard_branch` — the five steps, in order.**
  ```
  1. is_main -> ConflictError ; COUNT(branches WHERE root_id=?) <= 1 -> ConflictError
  2. nodes = aeroplanes WHERE branch_id = ?
  3. UPDATE aeroplanes SET predecessor_id = NULL
     WHERE predecessor_id IN {ids}      synchronize_session="fetch"
  4. db.delete(branch) ; db.flush()     ← BEFORE the nodes
  5. for node in nodes: db.delete(node) ; db.flush()
  ```
  - Legacy origin: `app/services/aeroplane_version_service.py:324-393`
  - Definition of done: **three failure tests** prove each step — deleting the
    nodes before the branch violates `branches.head_id NOT NULL`; skipping
    step 3 violates the `predecessor_id` FK on SQLite; both guards return 409.
    A surviving node keeps existing with `predecessor_id = null`.
  - Confidence: 🟢

- [ ] **T-07 — `list_tree`.**
  Confirm the root exists (404 otherwise); nodes
  `id == root_id OR root_id == root_id` ordered by `id`; branches
  `root_id == root_id` ordered by `id`.
  - Legacy origin: `app/services/aeroplane_version_service.py:415-456`
  - Definition of done: a node with a `NULL` `root_id` is **absent**
    (characterisation test — reproduce, then record the gap); ordering is
    deterministic.
  - Confidence: 🟢

- [ ] **T-08 — `list_aeroplanes_heads_only`.**
  `branch_id IS NULL` **OR** `id IN (SELECT head_id FROM branches)` — a scalar
  subquery, not a join — ordered by `name`.
  - Legacy origin: `app/services/aeroplane_version_service.py:515-534`
  - Definition of done: a legacy row is listed, an immutable snapshot is not,
    and the query count is one.
  - Confidence: 🟢

- [ ] **T-09 — The five routes.**
  `POST /aeroplanes/{aeroplane_id}/branch` (**201**),
  `POST /branches/{branch_id}/adopt` (200),
  `PATCH /branches/{branch_id}` (200),
  `DELETE /branches/{branch_id}` (**204**),
  `GET /lineages/{root_id}/tree` (200) — all **integer-PK** paths, with the
  `operation_id`s from [`../contracts.md`](../contracts.md).
  - Legacy origin: `app/api/v2/endpoints/versioning.py:143-160, 163-182,
    214-233, 236-258, 261-299`
  - Definition of done: contract tests per status code; the tree endpoint
    computes `is_head` from `{b.head_id}`.
  - Confidence: 🟢

- [ ] **T-10 — The schemas.**
  `BranchRequest{name (min 1), created_by? = "human"}` (`extra="forbid"`),
  `BranchRenameRequest{name (min 1)}` (`extra="forbid"`),
  `BranchOut{id, root_id, head_id, name, is_main, created_by?, created_at}`,
  `TreeNodeOut` (= `VersionNode` minus `preview_png` / `updated_at` /
  `provenance_message_id`, **plus `is_head`**), `TreeOut{root_id, nodes[],
  branches[]}`.
  - Legacy origin: `app/schemas/versioning.py`
  - Definition of done: `extra="forbid"` rejects an unknown field with a 422;
    `TreeNodeOut` is bandwidth-trimmed exactly as the legacy is.
  - Confidence: 🟢

- [ ] **T-11 — The migration's branch half.**
  Create `branches`; backfill one `main` branch per existing aeroplane with
  `INSERT … RETURNING id`; `UPDATE aeroplanes SET root_id = self,
  branch_id = <new>, is_immutable = 0`; create the partial index **after** the
  backfill.
  - Legacy origin: `alembic/versions/15f45e64a7c0_…`
  - Definition of done: N legacy aeroplanes ⇒ N main branches, no
    `branch_id IS NULL`; a test asserts `lastrowid` is **not** used (it is
    `None` on PostgreSQL and would leave every `branch_id` NULL).
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Partial index:** two mains for one `root_id` raise, on both
      backends; two non-mains do not.
- [ ] **TT-02 — Create:** head and `branch_id` back-filled; `is_main` false;
      forking from a snapshot allowed.
- [ ] **TT-03 — Create from a `NULL`-`root_id` node** starts a lineage rooted at
      that node (characterisation).
- [ ] **TT-04 — Duplicate names on create** are accepted (characterisation).
- [ ] **TT-05 — Adopt:** promotion + demotion; exactly one main; already-main
      409; mainless lineage promotes; **order-swap must fail**.
- [ ] **TT-06 — Rename:** strip · empty 422 · collision 409 · self-rename 200.
- [ ] **TT-07 — Discard guards:** main 409 · only-branch 409.
- [ ] **TT-08 — Discard ordering:** node-first fails; skipping the predecessor
      nulling fails; the correct order succeeds.
- [ ] **TT-09 — Discard cascade:** the nodes' wings, xsecs and component-tree
      rows are gone.
- [ ] **TT-10 — Survivor truncation:** a node whose predecessor was discarded
      keeps existing with `predecessor_id = null` (characterisation).
- [ ] **TT-11 — Tree:** ordering, `is_head` flags, unknown root 404,
      `NULL`-`root_id` node absent.
- [ ] **TT-12 — Heads-only:** legacy row listed, snapshot hidden, one query.
- [ ] **TT-13 — Transaction:** a rollback after `create_branch` leaves neither
      the branch nor the cloned head.
- [ ] **TT-14 — Logging:** each of the four mutating operations emits its
      `logger.info` with the expected ids.
- [ ] **TT-15 — Error envelope:** every 4xx body is `{"detail": …}`.

## Data Migration Tasks

- [ ] **TM-01 — Create `branches`** with both FKs in `use_alter` mode.
- [ ] **TM-02 — Backfill a `main` branch per aeroplane** using
      `INSERT … RETURNING id`; then set `root_id = self`, `branch_id`,
      `is_immutable = 0`.
- [ ] **TM-03 — Create the partial index after the backfill**, so a mid-flight
      state with two mains cannot violate it.
- [ ] **TM-04 — Leave any surviving `branch_id IS NULL` rows alone** — they
      remain visible through `list_aeroplanes_heads_only` by design (BR-VR3).

## Suggested Order

1. **T-01 → T-02** — the table and the index. The index is the invariant every
   later operation is written around, so it must exist before `adopt_branch` is
   even sketched.
2. **T-11** early, not last: the migration's backfill is the only step that
   touches existing data, and getting `INSERT … RETURNING` wrong is a
   production-only failure that no unit test would catch later.
3. **T-03** once the clone exists — `create_branch` is the foundation of
   `restore` and of the copilot's proposal branch.
4. **T-04** immediately after, with its order-swap failure test. This pair
   (index + demote-first) is the use case's core correctness story.
5. **T-06** next: discard is the only destructive path and needs three separate
   failure tests, so give it its own slot rather than bundling it with rename.
6. **T-05** (rename) any time after T-01 — it touches no other operation.
7. **T-07 → T-08** the read paths, which need a populated lineage.
8. **T-10 → T-09** schemas then routes, last.

## Pending Gaps

- **Should `create_branch` check for a name collision**, or should the database
  carry a `(root_id, name)` unique constraint? Today uniqueness is enforced on
  rename only.
- **Should `discard_branch` refuse to delete a node another node still descends
  from**, rather than nulling the link and truncating the survivor's lineage?
- **Should `list_tree` surface orphaned nodes** (`root_id IS NULL`) rather than
  omitting them silently?
- **Should forking from a `NULL`-`root_id` node be rejected**, instead of
  silently starting a new lineage?
- **Should adoption on a lineage with no main warn?** It currently succeeds
  quietly, hiding a failed backfill.
- **Should the routes accept UUIDs** like the rest of v2? `_get_node_by_uuid`
  already exists and is dead.
- **Should `head_id` advance** when a branch gains new work, or is the
  write-once behaviour the intended model?
- **Should the read paths paginate** for long-lived lineages?
- **Should the router log its catch-all 500s?**
</content>
