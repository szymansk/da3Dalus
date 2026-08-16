# versioning

> Module-level specification. Focuses on WHAT the module does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: versioning,
> `_reversa_sdd/data-dictionary.md` §Module: versioning,
> `_reversa_sdd/domain.md` §2.6, `_reversa_sdd/state-machines.md` §6,
> ADR 0006, ADR 0007, ADR 0009.

## Overview

`versioning` gives an aircraft design a **git-like history made of real rows**:
every version is a complete `aeroplanes` row with its own full subgraph — wings,
cross-sections, spars, fuselages, assumptions, stability results, component
tree — linked into a DAG by four columns and organised into named branches with
exactly one `main` per lineage. 🟢

There is no JSON snapshot anywhere (ADR 0006): a version *is* an aircraft, so
every read path in the rest of the system works on a historical version without
knowing it is one. 🟢

## Responsibilities

- Own `branches` and the nine versioning columns on `aeroplanes`. 🟢
- Snapshot a mutable head into an **immutable predecessor**. 🟢
- Fork a branch from any node — mutable head or frozen snapshot. 🟢
- Promote a branch to `main`, demoting the previous one. 🟢
- Restore an editable head from a snapshot. 🟢
- Discard a branch and its exclusive nodes, guarded. 🟢
- Rename a branch, unique per lineage at application level. 🟢
- Serve the lineage graph and a two-node metrics comparison. 🟢
- Own the **deep-clone engine** and its exhaustive coverage registry
  (`CLONED_TABLES` / `EXCLUDED_TABLES`). 🟢
- Record provenance — who made a version: `human`, `ai`, or `copilot`. 🟢

**Explicitly NOT this module's responsibility:** the lineage *bootstrap* on
aeroplane creation (→ `aeroplane-core`, BR-35), the copilot's proposal
lifecycle beyond the branch primitives it calls (→ `ai-copilot`, ADR 0007), and
the meaning of the cloned data itself (→ the owning modules).

## Business Rules

> `BR-35`…`BR-43` and `BR-78` are global ids reused verbatim from
> [`../domain.md`](../domain.md). `BR-VR*` are module-local.

### The data model

- **ADR 0006 — Versioning is row copy, not a JSON snapshot.** 🟢 The retired
  `design_versions` table was dropped by the gh-903 migration.
- **BR-VR1 — Four columns make the DAG.** 🟢
  ```
  root_id         the lineage root aeroplane — the ROOT POINTS AT ITSELF
  predecessor_id  self-referential: the node this one was forked from
  branch_id       FK → branches.id: which branch this node belongs to
  is_immutable    True = frozen snapshot ; False = editable head
  ```
  plus five metadata columns: `version_label`, `version_note`, `created_by`,
  `provenance_message_id` (FK → `copilot_messages.id`) and `preview_png`.
- **BR-VR2 — The FK cycle is real and resolved with `use_alter`.** 🟢
  `aeroplanes.branch_id → branches.id` and `branches.root_id/head_id →
  aeroplanes.id` form a cycle; all four constraints carry `use_alter=True` so
  Alembic emits them as separate `ALTER TABLE` statements.
- **BR-35 — Every aeroplane is a versioning node.** 🟢 `create_aeroplane`
  performs the three-step flush dance; the gh-903 migration backfilled the same
  shape for every pre-existing row using `INSERT … RETURNING id` (because
  `lastrowid` is `None` on PostgreSQL).
- **BR-36 — Exactly one `is_main` branch per lineage.** 🟢 Enforced by a
  **partial unique index**, declared identically in the model and the migration
  so `create_all` (tests) and a migrated production database agree:
  ```sql
  CREATE UNIQUE INDEX uq_branches_one_main_per_root ON branches (root_id)
    WHERE is_main = 1        -- sqlite_where ; postgresql_where: is_main = true
  ```
- **BR-VR3 — Legacy rows with `branch_id IS NULL` remain visible.** 🟢
  `list_aeroplanes_heads_only` returns branch heads **plus** every
  `branch_id IS NULL` row, so a pre-versioning aircraft never disappears from
  the picker.

### The operations

- **BR-37 — An immutable node can never be mutated.** 🟢 `_guard_immutable`
  raises `ValidationError` → 422 and is applied on `snapshot`. The mirror rule:
  `restore` **requires** `is_immutable=True`, because restoring from a live head
  is just `create_branch`.
- **BR-38 — A snapshot is inserted *behind* the head, not in front of it.** 🟢
  ```
  before:  [old_pred] ← [head (mutable, id=H)]
  after:   [old_pred] ← [snapshot (immutable, id=S)] ← [head (id=H, unchanged)]
  ```
  The head keeps its id, UUID and every inbound reference, which is why the UI
  never has to re-point after a snapshot.
- **BR-VR4 — `resolved_root_id = head.root_id or head.id`.** 🟢 Handles the
  root-snapshots-itself case, where the root's own `root_id` may be `NULL`.
- **BR-VR5 — The snapshot inherits the head's *old* predecessor.** 🟢
  `predecessor_id=head.predecessor_id` is passed to the clone **before** the
  head is re-pointed at the new snapshot.
- **BR-VR6 — `snapshot` hard-codes `created_by = "human"`.** 🟢
  (`aeroplane_version_service.py:172`) — regardless of who triggered it,
  including the copilot and the automatic spar-insert snapshot. 🔴
- **BR-VR7 — `adopt_branch` demotes first and flushes.** 🟢 The comment at
  `:277` states why: *"demote FIRST so the partial unique index never sees two
  `is_main=True`"*. Adopting an already-main branch is a `ConflictError` → 409.
- **BR-VR8 — `restore` defaults the branch name to `restore/<label>`.** 🟢
  Falling back to `restore/<node_id>` when the snapshot has no label.
- **BR-VR9 — `discard_branch`'s ordering is load-bearing.** 🟢
  ```
  1. guards: is_main -> 409 ; only branch of the lineage -> 409
  2. collect nodes WHERE branch_id = branch_id
  3. NULL OUT every predecessor_id pointing INTO that set
     (the FK is use_alter/deferred, but SQLite has no deferrable FKs)
  4. db.delete(branch) FIRST — otherwise SQLAlchemy nulls branches.head_id
     via the relationship and violates its NOT NULL constraint
  5. db.delete(node) for each node — the ORM cascade removes the owned subgraph
  ```
- **BR-42 — Branch names are unique per lineage at application level only.** 🟢
  `rename_branch` strips the name, rejects an empty result (422) and raises
  `ConflictError` (409) on a same-`root_id` collision. `create_branch` performs
  **no** collision check, so duplicates are reachable. 🔴
- **BR-VR10 — `compare` does not diff.** 🟢 It returns two `_metrics_payload`
  dicts and leaves the comparison to the client; there is no server-side
  structural diff since the `design_versions` diff endpoint was retired. 🔴
- **BR-VR11 — `list_tree` filters on `id == root_id OR root_id == root_id`.** 🟢
  A node whose `root_id` is `NULL` is therefore invisible in the version graph
  even though it exists. 🔴
- **BR-VR12 — Every versioning route takes an integer PK.** 🟢 The rest of the
  v2 API addresses aeroplanes by **UUID**. `_get_node_by_uuid` exists in the
  service (`:49`) and has **no caller**. 🔴

### The clone

- **BR-39 — The clone registry must be exhaustive.** 🟢 Every table with a
  transitive FK to `aeroplanes` appears in exactly one of `CLONED_TABLES` (17)
  or `EXCLUDED_TABLES` (18), asserted by `test_aeroplane_clone_coverage.py`,
  which also asserts the two sets are disjoint and that every exclusion carries
  a non-empty reason.
  **Blind spot:** the test introspects SQLAlchemy `ForeignKey` objects, so
  tables whose aeroplane reference is a plain `String` are invisible to it and
  must be registered by hand — `component_tree` (cloned),
  `construction_plans` and `construction_parts` (excluded). 🔴
- **BR-40 — Cloning re-keys internal references and keeps shared ones.** 🟢
  `loading_scenarios.component_overrides[*].component_uuid` is remapped through
  a `weight_id_map`; values **not** in the map pass through unchanged because
  they are COTS component UUIDs. `flight_profile_id`, `servo.component_id`,
  `component_tree.component_id` / `construction_part_id` / `material_id` are
  kept as shared references. New `uuid4`; `fuselages.step_path` /
  `solid_step_path` → `NULL`; the five version-metadata columns → `None`.
- **BR-VR13 — The component tree is cloned in two passes.** 🟢 Pass 1 inserts
  every node with `parent_id=None`, collecting `old_id → new_id`; pass 2 issues
  an `UPDATE` per node to restore the parent link. A parent not in the map
  leaves `parent_id = None` and logs a **warning naming both ids** — chosen
  explicitly over silent data loss.
- **BR-VR14 — The clone never commits.** 🟢 `db.flush()` after each group so
  auto-generated PKs are available for FK re-keying; `get_db()` owns the
  boundary (ADR 0009, BR-78).

### Provenance

- **BR-VR15 — Four writers, three vocabularies, no enum.** 🟢
  | Writer | Value |
  |---|---|
  | `aeroplane_service.create_aeroplane` (main branch) | `"human"` |
  | `aeroplane_version_service.snapshot` (snapshot node) | `"human"` (hard-coded) |
  | `versioning.py` REST (`BranchRequest.created_by`) | `"human"` by default; the schema documents `'human' \| 'ai'` |
  | `copilot_apply_service.get_or_open_proposal` | **`"copilot"`** |
  🔴 Any UI filtering on `'ai'` misses every copilot branch.
- **BR-VR16 — `provenance_message_id` is write-only.** 🟢 Accepted by
  `SnapshotRequest`, written by `snapshot()`, returned on `VersionNode` — and
  read by nothing. 🔴
- **BR-41 — Never mutate destructively without a recovery point.** 🟢 (gh-1058)
  A destructive spar commit takes an automatic immutable snapshot labelled
  `"Before spar insert"` **before** mutating anything and **aborts the whole
  commit if the snapshot fails**; the snapshot id is returned so the UI can
  offer one-click revert.
- **BR-43 / ADR 0007 — The copilot proposes; only a human adopts.** 🟢 Write
  tools operate exclusively on a `copilot-proposal` branch.
- 🟡 **`preview_png`** — the column, the clone reset and the `VersionNode` field all exist; no code path generates a thumbnail (`Q-VS-2`). is never written.** The column exists, is cloned as `None`
  and is surfaced on `VersionNode`; no code path generates a thumbnail.
- 🔴 **The `design-versions` REST surface is dead but still mounted.** All five
  routes call a stub that unconditionally raises `NotFoundError`, so callers get
  a plausible 404 rather than a 410/501.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Snapshot a mutable head into an immutable predecessor | Must | `POST /aeroplanes/{id}/snapshot` → **201**; the head's id is unchanged and its `predecessor_id` now points at the snapshot |
| RF-02 | Refuse to snapshot an already-immutable node | Must | → 422 |
| RF-03 | Carry `label`, `note` and `provenance_message_id` onto the snapshot | Must | All three are readable on the returned `VersionNode` |
| RF-04 | Resolve the lineage root when the head is the root | Must | A snapshot of the root carries `root_id == root.id` |
| RF-05 | Fork a branch from any node, creating a mutable head | Must | `POST /aeroplanes/{id}/branch` → **201** `BranchOut` with `is_main=false` |
| RF-06 | Back-fill the new head's `branch_id` after the branch row exists | Must | The cloned head's `branch_id` equals the new branch's id |
| RF-07 | Promote a branch to main, demoting the previous one | Must | `POST /branches/{id}/adopt` → 200; exactly one `is_main` row remains for the lineage |
| RF-08 | Refuse to adopt an already-main branch | Must | → 409 |
| RF-09 | Restore an editable branch from an immutable snapshot | Must | `POST /aeroplanes/{snapshot_id}/restore` → **201**; default name `restore/<label>` |
| RF-10 | Refuse to restore from a mutable node | Must | → 422 |
| RF-11 | Discard a branch and its exclusive nodes | Must | `DELETE /branches/{id}` → **204**; the branch and its nodes are gone |
| RF-12 | Refuse to discard the main branch or the only branch | Must | Both → 409 |
| RF-13 | Null inbound `predecessor_id` links before deleting | Must | Surviving nodes keep existing with `predecessor_id = null` |
| RF-14 | Rename a branch, stripped and unique per lineage | Must | `PATCH /branches/{id}` → 200; a collision → 409; an empty name → 422 |
| RF-15 | Return the lineage graph with a computed `is_head` flag | Must | `GET /lineages/{root_id}/tree` → 200 with nodes and branches; `is_head` true for every `branch.head_id` |
| RF-16 | Compare two nodes by returning both metrics payloads | Must | `GET /aeroplanes/compare?a=&b=` → 200 with `metrics_a` and `metrics_b` |
| RF-17 | Deep-clone the 17 owned tables, re-keying every internal FK | Must | A clone's wings, xsecs, spars, TEDs, servos, turbulators, fuselages, weight items, mission objective, assumptions, config, stability results, loading scenarios and component tree all exist with new PKs |
| RF-18 | Keep shared references unchanged | Must | `flight_profile_id`, `servo.component_id`, `component_tree.component_id` / `construction_part_id` / `material_id` are identical in source and clone |
| RF-19 | Remap `loading_scenarios.component_overrides` through the weight-id map | Must | A clone's scenario references the **clone's** weight items, not the source's |
| RF-20 | Clone the component tree in two passes, preserving parentage | Must | The clone's tree has the same shape; an unmappable parent leaves `parent_id = null` and logs both ids |
| RF-21 | Null `step_path` / `solid_step_path` and the five version-metadata columns | Must | The clone carries no stale artefact paths and no inherited label |
| RF-22 | Keep the clone registry exhaustive and disjoint | Must | `test_aeroplane_clone_coverage` passes; every exclusion has a non-empty reason |
| RF-23 | Never commit inside the clone or any versioning operation | Must | A rollback after a snapshot leaves no partial version |
| RF-24 | Record `created_by` on branches and nodes | Should | A copilot branch carries `"copilot"`; a REST branch defaults to `"human"` |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Integrity | The one-main-per-lineage rule is enforced by the **schema**, not only by code | `uq_branches_one_main_per_root` in both the model and the migration | 🟢 |
| Integrity | The clone registry is enforced by a test, and every exclusion must justify itself | `test_aeroplane_clone_coverage.py` | 🟢 |
| Integrity | A destructive edit is preceded by a recovery point, and aborts if it cannot be taken | `spar_insert_service.py:485-497`; gh-1058 | 🟢 |
| Correctness | A snapshot preserves the head's identity, so no inbound reference is invalidated | `snapshot:150-183`; BR-38 | 🟢 |
| Correctness | Deletion order is chosen to satisfy a non-deferrable FK graph on SQLite | `discard_branch:361-387` | 🟢 |
| Correctness | Unmappable data is logged with both ids rather than silently dropped | `_clone_component_tree:565-580` | 🟢 |
| Reliability | Every operation runs inside the caller's transaction (ADR 0009) | module docstring, `app/db/session.py:55-64` | 🟢 |
| Portability | The partial index is declared for both SQLite and PostgreSQL | model + migration | 🟢 |
| Scalability | **No** storage-growth control: every snapshot is a full row copy of the entire design subgraph, with no retention policy or size accounting | `clone_aeroplane_subgraph` | 🟡 |
| Security | No authentication; the tunnel is the trust boundary (ADR 0016) | — | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Snapshot

  Scenario: A snapshot is inserted behind the head
    Given a mutable head H with predecessor P
    When I snapshot H with label "before spar"
    Then a new immutable node S exists
    And S.predecessor_id is P
    And H.predecessor_id is S
    And H keeps its id and uuid

  Scenario: An immutable node cannot be snapshotted
    Given an immutable snapshot node
    When I POST /aeroplanes/{id}/snapshot
    Then the response status is 422

  Scenario: Snapshotting the root resolves its own root_id
    Given a lineage root whose root_id equals its own id
    When I snapshot it
    Then the snapshot's root_id is the root's id

Feature: Branch

  Scenario: Forking creates a mutable head and a branch row
    Given any node N
    When I POST /aeroplanes/{N}/branch with name "experiment"
    Then the response status is 201
    And a new branch exists with is_main false
    And its head is a new mutable aeroplane whose predecessor_id is N
    And that head's branch_id is the new branch's id

  Scenario: Adopting promotes and demotes atomically
    Given a lineage with main branch M and feature branch F
    When I POST /branches/{F}/adopt
    Then F.is_main is true
    And M.is_main is false
    And exactly one branch of the lineage has is_main true

  Scenario: Adopting the main branch is a conflict
    When I POST /branches/{main}/adopt
    Then the response status is 409

  Scenario: Renaming enforces per-lineage uniqueness
    Given branches "a" and "b" in one lineage
    When I PATCH branch "b" to name "a"
    Then the response status is 409
    When I PATCH branch "b" to name "   "
    Then the response status is 422

  Scenario: Creating does NOT enforce uniqueness
    Given a branch named "a"
    When I create another branch named "a" in the same lineage
    Then the response status is 201
    And two branches share the name

Feature: Restore and discard

  Scenario: Restore requires an immutable node
    Given a mutable head
    When I POST /aeroplanes/{id}/restore
    Then the response status is 422

  Scenario: Restore defaults its branch name
    Given an immutable snapshot labelled "before spar"
    When I POST /aeroplanes/{id}/restore without a name
    Then the new branch is named "restore/before spar"

  Scenario: The main branch cannot be discarded
    When I DELETE /branches/{main}
    Then the response status is 409

  Scenario: The only branch cannot be discarded
    Given a lineage with a single branch
    When I DELETE it
    Then the response status is 409

  Scenario: Discarding nulls inbound predecessor links
    Given node X on branch A whose predecessor is node Y on branch B
    When I discard branch B
    Then X still exists
    And X.predecessor_id is null

Feature: Clone fidelity

  Scenario: The subgraph is deep-copied with new PKs
    Given an aircraft with wings, xsecs, spares, TEDs, servos, a fuselage,
      weight items, assumptions, stability results, loading scenarios and a component tree
    When I snapshot it
    Then every one of those tables has new rows for the snapshot
    And no row is shared with the source

  Scenario: Shared references are preserved
    When I clone an aircraft
    Then flight_profile_id, servo.component_id and component_tree.component_id
      are identical in source and clone

  Scenario: Loading-scenario overrides are re-keyed
    Given a loading scenario referencing weight item 7 by component_uuid "7"
    When I clone the aircraft
    Then the clone's scenario references the clone's copy of that weight item

  Scenario: STEP paths and version metadata are cleared
    When I clone an aircraft whose fuselage has a step_path
    Then the clone's step_path is null
    And version_label, version_note, created_by, provenance_message_id and
      preview_png are all null on the clone

  Scenario: An unmappable tree parent is logged, not dropped silently
    Given a component-tree node whose parent belongs to another aeroplane
    When I clone the aircraft
    Then the cloned node's parent_id is null
    And a warning naming both ids is logged
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Snapshot with identity preservation (RF-01…RF-04) | Must | The recovery point every destructive edit depends on (BR-41) |
| Branch create + adopt with the demote-first rule (RF-05…RF-08) | Must | The partial unique index makes a wrong order a hard database error |
| Restore + its immutability requirement (RF-09/RF-10) | Must | The undo path |
| Discard with its three guards and the deletion order (RF-11…RF-13) | Must | The only destructive operation in the module; the ordering is not optional on SQLite |
| Clone fidelity + registry exhaustiveness (RF-17…RF-22) | Must | A missed table means silently shared state between two "independent" versions |
| No commit inside the operations (RF-23) | Must | ADR 0009; a partial version is unrecoverable |
| Rename with per-lineage uniqueness (RF-14) | Should | Convenience; `create_branch` already allows duplicates |
| Lineage tree + `is_head` (RF-15) | Should | The version-graph UI; the data is reachable without it |
| Two-node comparison (RF-16) | Should | Read-only decoration over `_metrics_payload` |
| `created_by` provenance (RF-24) | Should | Informational; no behaviour keys off it today |
| Server-side structural diff | Won't | 🟡 retired with `design_versions`; `compare` returns two payloads |
| Snapshot retention / pruning | Won't | 🟡 not implemented — unbounded growth |
| `preview_png` thumbnails | Won't | 🟡 the column exists and is never written |
| UUID-addressed versioning routes | Won't | 🟡 `_get_node_by_uuid` exists and is never called |
| The `design-versions` routes | Won't | 🟡 dead — every one raises `NotFoundError` |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/models/aeroplanemodel.py:602-660` | `BranchModel` + `uq_branches_one_main_per_root` | 🟢 |
| `app/models/aeroplanemodel.py:662-716` | the 9 versioning columns + 4 `use_alter` FKs | 🟢 |
| `app/services/aeroplane_version_service.py:41-118` | `_get_node`, `_get_branch`, `_guard_immutable`, `_metrics_payload` | 🟢 |
| `…:49` | `_get_node_by_uuid` | 🟡 dead — no caller |
| `…:125-183` | `snapshot` | 🟢 |
| `…:186-241` | `create_branch` | 🟢 |
| `…:244-288` | `adopt_branch` (demote-first + flush) | 🟢 |
| `…:291-321` | `restore` | 🟢 |
| `…:324-393` | `discard_branch` (the five-step order) | 🟢 |
| `…:396-412` | `compare` | 🟢 |
| `…:415-456` | `list_tree` | 🟢 |
| `…:459-512` | `rename_branch` | 🟢 |
| `…:515-534` | `list_aeroplanes_heads_only` | 🟢 |
| `app/services/aeroplane_clone_service.py:70-132` | `CLONED_TABLES` (17) / `EXCLUDED_TABLES` (18) + the blind-spot note | 🟢 |
| `…:140-455` | `clone_aeroplane_subgraph` (10 groups) | 🟢 |
| `…:463-491` | `_remap_component_overrides` | 🟢 |
| `…:494-580` | `_clone_component_tree` (two passes) | 🟢 |
| `app/api/v2/endpoints/versioning.py` | 8 routes + `_raise_http` / `_call` | 🟢 |
| `app/schemas/versioning.py` | `SnapshotRequest`, `BranchRequest`, `BranchRenameRequest`, `VersionNode`, `TreeNodeOut`, `BranchOut`, `TreeOut`, `CompareOut` | 🟢 |
| `alembic/versions/15f45e64a7c0_gh903_versioning_db_model.py` | schema + backfill + `DROP TABLE design_versions` | 🟢 |
| `app/tests/test_aeroplane_clone_coverage.py` | the coverage invariant | 🟢 |
| `app/services/aeroplane_service.py:61-104` | the lineage bootstrap | 🟢 owned by `aeroplane-core` |
| `app/services/copilot_apply_service.py:107-241` | the proposal lifecycle | 🟢 owned by `ai-copilot` |
| `app/services/spar_insert_service.py:485-497` | the automatic pre-mutation snapshot | 🟢 owned by `wing-design` |
| `app/services/design_version_service.py` + `aeroplane/design_versions.py` | 5 routes over a raising stub | 🟡 dead but mounted |
</content>
