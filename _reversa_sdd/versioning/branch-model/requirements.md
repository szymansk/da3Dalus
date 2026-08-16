# branch-model

> Use-case specification, nested under the module
> [`versioning`](../requirements.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Sources: `app/models/aeroplanemodel.py:602-716`,
> `app/services/aeroplane_version_service.py:186-393, 415-534`,
> `app/api/v2/endpoints/versioning.py`,
> `alembic/versions/15f45e64a7c0_…`, `_reversa_sdd/state-machines.md` §6.
> Endpoint contract: [`../contracts.md`](../contracts.md).

## Overview

The **branch layer**: named pointers into a lineage, with exactly one `main` per
lineage enforced by a partial unique index, and the four operations that move
them — create, adopt, rename, discard — plus the two read paths that render the
version graph and the aeroplane picker. 🟢

Everything here is about *pointers and guards*; the copying itself belongs to
[`aeroplane-clone-subgraph`](../aeroplane-clone-subgraph/requirements.md) and
the freezing to
[`snapshot-immutability`](../snapshot-immutability/requirements.md).

## Responsibilities

- Own `branches` and the partial unique index. 🟢
- Fork a branch from any node into a new mutable head. 🟢
- Promote a branch to `main`, demoting the previous one. 🟢
- Rename a branch, unique per lineage at application level. 🟢
- Discard a branch and its exclusive nodes, guarded and in a load-bearing
  order. 🟢
- Serve the lineage graph with a computed `is_head` flag. 🟢
- Serve the branch-heads-only aeroplane list, including legacy rows. 🟢

**NOT this use case:** snapshots and immutability
(→ [`snapshot-immutability`](../snapshot-immutability/requirements.md)), the
deep copy (→ [`aeroplane-clone-subgraph`](../aeroplane-clone-subgraph/requirements.md)),
`created_by` semantics (→ [`copilot-provenance`](../copilot-provenance/requirements.md)),
and the lineage bootstrap on aeroplane creation (→ `aeroplane-core`).

## Business Rules

> Global ids from [`../../domain.md`](../../domain.md); `BR-VR*` from
> [`../requirements.md`](../requirements.md); `BR-BM*` are new here.

- **BR-VR1 — Four columns make the DAG.** 🟢 `root_id` (the root points at
  **itself**), `predecessor_id`, `branch_id`, `is_immutable`.
- **BR-36 — Exactly one `is_main` branch per lineage root.** 🟢 A **partial**
  unique index, declared identically in the model and the migration:
  ```sql
  CREATE UNIQUE INDEX uq_branches_one_main_per_root ON branches (root_id)
    WHERE is_main = 1     -- sqlite_where ; postgresql_where: is_main = true
  ```
- **BR-VR2 — The FK cycle is real.** 🟢 `aeroplanes.branch_id → branches.id` and
  `branches.root_id/head_id → aeroplanes.id`; all four constraints carry
  `use_alter=True`, and the relationships use explicit `foreign_keys=` to
  disambiguate the two FKs into the same table.
- **BR-BM1 — Creating a branch is a three-flush dance.** 🟢
  clone with `branch_id=None` → flush (obtain `new_head.id`) → insert
  `BranchModel(head_id=new_head.id)` → flush (obtain `branch.id`) → back-fill
  `new_head.branch_id` → flush. The circular FK pair cannot be satisfied in one
  statement (`create_branch:207-232`).
- **BR-BM2 — A branch may be forked from a head *or* a snapshot.** 🟢
  `create_branch` applies **no** immutability guard — which is precisely what
  lets `restore` be a thin wrapper over it.
- **BR-BM3 — A new branch is never main.** 🟢 `is_main=False` at creation;
  promotion is a separate, explicit operation.
- **BR-VR7 — `adopt_branch` demotes first and flushes.** 🟢 The comment at
  `:277` states why: *"demote FIRST so the partial unique index never sees two
  `is_main=True`"*. Adopting an already-main branch is a `ConflictError` → 409.
  The demoted branch is **kept**, not deleted.
- **BR-BM4 — Adoption tolerates a lineage with no current main.** 🟢
  `current_main is None` skips the demote and promotes anyway — reachable for a
  legacy lineage whose backfill did not run. 🟡
- **BR-42 — Branch names are unique per lineage at application level only.** 🟢
  `rename_branch` strips the name, raises `ValidationError` (422) on an empty
  result and `ConflictError` (409) on a same-`root_id` collision **excluding
  itself**. `create_branch` performs no check at all. 🔴
- **BR-VR9 — `discard_branch`'s five steps are load-bearing.** 🟢
  ```
  1. guards      is_main -> 409 ;  COUNT(branches WHERE root_id=?) <= 1 -> 409
  2. collect     nodes WHERE branch_id = ?
  3. null out    UPDATE aeroplanes SET predecessor_id = NULL
                 WHERE predecessor_id IN {node ids}
                 (the FK is use_alter/deferred, but SQLite has no deferrable FKs)
  4. delete branch FIRST   (otherwise SQLAlchemy nulls branches.head_id via the
                            relationship and violates its NOT NULL constraint)
  5. delete each node      (the ORM cascade removes the owned subgraph)
  ```
- **BR-BM5 — Discard selects nodes by `branch_id` alone.** 🟢 A snapshot created
  on branch A is deleted with A regardless of what still descends from it;
  step 3 simply nulls those links. 🔴
- **BR-BM6 — `list_tree` filters on `id == root_id OR root_id == root_id`.** 🟢
  A node whose `root_id` is `NULL` is therefore invisible in the graph even
  though it exists. 🔴 Nodes and branches are both ordered by `id`.
- **BR-BM7 — `is_head` is computed at the endpoint.** 🟢
  `node.id in {b.head_id for b in branches}` — it is not a column
  (`versioning.py:277-296`).
- **BR-VR3 — Legacy rows stay visible.** 🟢 `list_aeroplanes_heads_only` returns
  `branch_id IS NULL` **OR** `id IN (SELECT head_id FROM branches)`, ordered by
  `name`.
- **BR-BM8 — A branch's `head_id` never advances.** 🟢 It is set at creation and
  never updated in the code read here — coherent with BR-38, since a snapshot
  inserts itself *behind* the head rather than replacing it. 🟡
- **BR-VR12 — 🟢 Every route exposes the public UUID (`Q-VS-8`, ADR 0019). Previously an integer PK, inconsistent with the
  UUID-addressed rest of v2.
- **BR-78 / ADR 0009 — No commit.** 🟢

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Enforce one `is_main` branch per lineage at the schema level | Must | A second `is_main=true` insert for the same `root_id` raises an `IntegrityError` on SQLite **and** PostgreSQL |
| RF-02 | Fork a branch from any node into a new mutable head | Must | `POST /aeroplanes/{id}/branch` → **201**; the head is mutable, its `predecessor_id` is the source |
| RF-03 | Back-fill the head's `branch_id` after the branch row exists | Must | `head.branch_id == branch.id` after the call |
| RF-04 | Allow forking from an immutable snapshot | Must | A snapshot id is accepted; no 422 |
| RF-05 | Create every branch with `is_main = false` | Must | A freshly created branch is never main |
| RF-06 | Promote a branch, demoting the previous main first | Must | `POST /branches/{id}/adopt` → 200; exactly one `is_main` remains; swapping the order fails with an `IntegrityError` |
| RF-07 | Refuse to adopt an already-main branch | Must | → 409 |
| RF-08 | Rename a branch, stripped, unique per lineage | Must | `PATCH /branches/{id}` → 200; collision → 409; `"   "` → 422; renaming to its own name succeeds |
| RF-09 | Discard a branch and its exclusive nodes | Must | `DELETE /branches/{id}` → **204**; the branch and its nodes are gone with their subgraphs |
| RF-10 | Refuse to discard the main branch or the only branch | Must | Both → 409 |
| RF-11 | Null inbound `predecessor_id` links before deleting | Must | A surviving node keeps existing with `predecessor_id = null` |
| RF-12 | Delete the branch row before its nodes | Must | The reverse order violates `branches.head_id NOT NULL` |
| RF-13 | Serve the lineage graph with nodes and branches ordered by id | Must | `GET /lineages/{root_id}/tree` → 200; unknown root → 404 |
| RF-14 | Compute `is_head` per node from the branches' `head_id`s | Must | Exactly the branch heads carry `is_head = true` |
| RF-15 | List branch heads plus legacy rows for the aeroplane picker | Must | A `branch_id IS NULL` row is listed; an immutable snapshot is not |
| RF-16 | Run every operation inside the caller's transaction | Must | A rollback leaves no branch and no node |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Integrity | The one-main rule is a database constraint, not a code convention — a wrong write is impossible, not merely unlikely | `uq_branches_one_main_per_root` in model **and** migration | 🟢 |
| Portability | The partial index is declared for both SQLite and PostgreSQL so tests and production agree | `sqlite_where` / `postgresql_where` | 🟢 |
| Correctness | Deletion order is derived from SQLite's lack of deferrable FKs, and is documented in the code | `discard_branch:361-387` | 🟢 |
| Correctness | The circular FK pair is satisfied by an explicit flush sequence rather than by disabling constraints | `create_branch:207-232` | 🟢 |
| Reliability | Every operation runs in the request transaction and never commits (ADR 0009) | module docstring | 🟢 |
| Observability | Every mutating operation logs its ids and the affected counts | `logger.info` in all four | 🟢 |
| Performance | `list_tree` is two indexed queries; `list_aeroplanes_heads_only` is one query with a scalar subquery | `:439-454, 524-533` | 🟢 |
| Scalability | No pagination on either read path — a long-lived lineage returns every node in one response | `list_tree` | 🟡 |

## Acceptance Criteria

```gherkin
Feature: One main branch per lineage

  Scenario: The database refuses a second main
    Given a lineage whose main branch exists
    When a second branch row with is_main true and the same root_id is inserted
    Then the database raises an integrity error

  Scenario: Adoption demotes before promoting
    Given a lineage with main branch M and feature branch F
    When I adopt F
    Then F.is_main is true
    And M.is_main is false
    And exactly one branch of the lineage is main

  Scenario: Adopting the main branch is a conflict
    When I adopt the branch that is already main
    Then the response status is 409

Feature: Branch creation

  Scenario: Forking from a mutable head
    Given a mutable head H
    When I POST /aeroplanes/{H}/branch with name "experiment"
    Then the response status is 201
    And a branch named "experiment" exists with is_main false
    And its head is a new mutable aeroplane whose predecessor_id is H
    And that head's branch_id is the branch's id

  Scenario: Forking from an immutable snapshot
    Given an immutable snapshot S
    When I POST /aeroplanes/{S}/branch with name "from-snapshot"
    Then the response status is 201

  Scenario: Duplicate names are allowed on create
    Given a branch named "a" in a lineage
    When I create another branch named "a" in the same lineage
    Then the response status is 201
    And two branches share the name

Feature: Rename

  Scenario: Whitespace is stripped
    When I PATCH a branch to name "  tidy  "
    Then the stored name is "tidy"

  Scenario: An empty name is rejected
    When I PATCH a branch to name "   "
    Then the response status is 422

  Scenario: A collision within the lineage is rejected
    Given branches "a" and "b" in one lineage
    When I PATCH "b" to name "a"
    Then the response status is 409

  Scenario: Renaming a branch to its own name succeeds
    Given a branch named "a"
    When I PATCH it to name "a"
    Then the response status is 200

Feature: Discard

  Scenario: The main branch cannot be discarded
    When I DELETE the main branch
    Then the response status is 409

  Scenario: The only branch cannot be discarded
    Given a lineage with exactly one branch
    When I DELETE it
    Then the response status is 409

  Scenario: Discarding removes the branch and its nodes
    Given a feature branch with two nodes
    When I DELETE it
    Then the response status is 204
    And neither node exists
    And their wings and component-tree nodes are gone

  Scenario: Inbound predecessor links are nulled, not blocked
    Given node X on branch A whose predecessor is node Y on branch B
    When I discard branch B
    Then X still exists
    And X.predecessor_id is null

Feature: Read paths

  Scenario: The lineage graph marks its heads
    Given a lineage with two branches
    When I GET /lineages/{root_id}/tree
    Then every branch head node has is_head true
    And every other node has is_head false

  Scenario: An orphaned node is invisible
    Given a node whose root_id is null
    When I GET the lineage tree
    Then that node is absent

  Scenario: The picker shows heads and legacy rows
    Given a lineage with one head and one snapshot, and one legacy row with branch_id null
    When I list aeroplanes with heads_only
    Then the head and the legacy row are listed
    And the snapshot is not
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| The partial unique index (RF-01) | Must | The lineage's single most important invariant, and the reason the adopt order matters |
| Branch creation with the flush dance (RF-02…RF-05) | Must | Without the back-fill the head is orphaned from its branch |
| Adopt with demote-first (RF-06/RF-07) | Must | The wrong order is a hard database error, not a soft bug |
| Discard guards + ordering (RF-09…RF-12) | Must | The only destructive operation; each step prevents a concrete failure |
| Transaction discipline (RF-16) | Must | ADR 0009 — a half-created branch is unrecoverable |
| Lineage tree + `is_head` (RF-13/RF-14) | Should | The version-graph UI; the data is reachable without it |
| Heads-only listing (RF-15) | Should | Keeps snapshots out of the picker; legacy visibility is a compatibility promise |
| Rename with uniqueness (RF-08) | Should | Convenience — `create_branch` already permits duplicates |
| A `(root_id, name)` unique constraint | Won't | 🟡 not implemented; uniqueness is app-level and one-sided |
| Advancing `head_id` on new commits | Won't | 🟡 the head never moves; snapshots insert behind it |
| Pagination of the lineage tree | Won't | Not implemented |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/models/aeroplanemodel.py:602-660` | `BranchModel` + `uq_branches_one_main_per_root` | 🟢 |
| `app/models/aeroplanemodel.py:662-716` | `branch_id`, `predecessor_id`, `root_id`, `is_immutable` | 🟢 |
| `app/services/aeroplane_version_service.py:186-241` | `create_branch` | 🟢 |
| `…:244-288` | `adopt_branch` | 🟢 |
| `…:324-393` | `discard_branch` | 🟢 |
| `…:415-456` | `list_tree` | 🟢 |
| `…:459-512` | `rename_branch` | 🟢 |
| `…:515-534` | `list_aeroplanes_heads_only` | 🟢 |
| `app/api/v2/endpoints/versioning.py:143-160, 163-182, 214-233, 236-258, 261-299` | the five branch routes | 🟢 |
| `app/schemas/versioning.py` | `BranchRequest`, `BranchRenameRequest`, `BranchOut`, `TreeNodeOut`, `TreeOut` | 🟢 |
| `alembic/versions/15f45e64a7c0_…` | `branches` + the partial index + the backfill | 🟢 |
</content>
