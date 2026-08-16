# snapshot-immutability

> Use-case specification, nested under the module
> [`versioning`](../requirements.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Sources: `app/services/aeroplane_version_service.py:65-71, 125-183, 291-321`,
> `app/services/spar_insert_service.py:485-497`,
> `app/api/v2/endpoints/versioning.py`, `_reversa_sdd/state-machines.md` §6,
> ADR 0006. Endpoint contract: [`../contracts.md`](../contracts.md).

## Overview

A **snapshot** is a frozen aircraft. This use case owns the two-valued node
state (`is_immutable`), the counter-intuitive insertion topology that keeps the
head's identity intact, the mirror-image guards on `snapshot` and `restore`, and
the automatic recovery point that a destructive spar edit is required to take
before touching anything. 🟢

The single sentence that explains the whole design: **a snapshot is inserted
*behind* the head, not in front of it.** 🟢

## Responsibilities

- Freeze the current state of a mutable head into an immutable predecessor. 🟢
- Refuse to mutate an immutable node. 🟢
- Refuse to restore from a mutable one. 🟢
- Carry `version_label`, `version_note` and `provenance_message_id` onto the
  snapshot. 🟢
- Fork an editable branch back out of a frozen node. 🟢
- Provide the recovery point that `spar_insert_service` takes — and aborts
  on. 🟢

**NOT this use case:** branch pointers and the discard path
(→ [`branch-model`](../branch-model/requirements.md)), the copy itself
(→ [`aeroplane-clone-subgraph`](../aeroplane-clone-subgraph/requirements.md)),
and who is recorded as the author
(→ [`copilot-provenance`](../copilot-provenance/requirements.md)).

## Business Rules

> Global ids from [`../../domain.md`](../../domain.md); `BR-VR*` from
> [`../requirements.md`](../requirements.md); `BR-SN*` are new here.

- **BR-37 — An immutable node can never be mutated.** 🟢 `_guard_immutable`
  (`:65-71`) raises `ValidationError("Cannot mutate an immutable snapshot
  node")` with `node_id` and `is_immutable` in `details` → **422**. It is
  applied on `snapshot`.
- **BR-SN1 — The mirror rule.** 🟢 `restore` **requires** `is_immutable=True`
  and raises `ValidationError("restore() requires an immutable snapshot node")`
  otherwise — because restoring from a live head is already `create_branch`.
- **BR-38 — A snapshot is inserted *behind* the head.** 🟢
  ```
  before:  [old_pred] ← [head (mutable, id=H)]
  after:   [old_pred] ← [snapshot (immutable, id=S)] ← [head (id=H, unchanged)]
  ```
  The head keeps its **id, uuid and every inbound reference**, which is why no
  caller has to re-point after a snapshot.
- **BR-VR4 — `resolved_root_id = head.root_id if head.root_id is not None else
  head.id`.** 🟢 Handles the root-snapshots-itself case, where the lineage
  root's own `root_id` may be `NULL`. Without it the snapshot would be invisible
  to `list_tree`.
- **BR-VR5 — The snapshot inherits the head's *old* predecessor.** 🟢
  `predecessor_id=head.predecessor_id` is passed to the clone **before**
  `head.predecessor_id` is re-pointed at the new snapshot — so the chain stays
  linear.
- **BR-SN2 — The snapshot stays on the head's branch.** 🟢
  `branch_id=head.branch_id`; a snapshot is not a branch of its own. Consequence:
  `discard_branch` removes it along with the branch
  ([`branch-model`](../branch-model/requirements.md) BR-BM5).
- **BR-SN3 — Version metadata is set after the clone, not during it.** 🟢 The
  clone always writes `version_label`/`version_note`/`created_by`/
  `provenance_message_id`/`preview_png` as `None`; `snapshot` then assigns four
  of them and flushes.
- **BR-VR6 — `created_by` on the snapshot node is hard-coded `"human"`.** 🟢
  (`:172`) — regardless of the caller, including the copilot and the automatic
  spar-insert snapshot. 🔴
- **BR-SN4 — Two flushes, in order.** 🟢 The first obtains `snapshot_node.id`;
  only then can `head.predecessor_id` be set and flushed. Reversing them leaves
  the head pointing at `None`.
- **BR-VR8 — `restore` names the branch `restore/<label>`.** 🟢 Falling back to
  `restore/<node_id>` when the snapshot carries no `version_label`; an explicit
  `name` overrides both.
- **BR-SN5 — `restore` is `create_branch` under a guard.** 🟢 After the
  immutability check it delegates verbatim, so the new head is a **mutable**
  clone of the frozen node with `predecessor_id = snapshot_node_id`.
- **BR-41 — Never mutate destructively without a recovery point.** 🟢 (gh-1058)
  `spar_insert_service` (`:485-497`) takes an automatic immutable snapshot
  labelled **`"Before spar insert"`** *before* a segment split or a spare
  REPLACE, and **aborts the whole commit if the snapshot fails**. The snapshot
  id is returned in `SparInsertResponse` so the UI can offer one-click revert.
- **BR-SN6 — `is_immutable` is NOT NULL with `server_default="false"`.** 🟢
  Every aeroplane is mutable unless explicitly frozen; there is no third state.
- **BR-SN7 — Immutability is enforced only where it is checked.** 🟢
  `_guard_immutable` is applied on `snapshot`; **no** database constraint, ORM
  event or trigger prevents an ordinary `PUT /wings/...` from writing to an
  immutable node. 🔴
- **BR-78 / ADR 0009 — No commit.** 🟢

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Freeze a mutable head into an immutable predecessor | Must | `POST /aeroplanes/{id}/snapshot` → **201** returning the **snapshot** node, `is_immutable = true` |
| RF-02 | Preserve the head's identity | Must | The head's `id` and `uuid` are unchanged after the snapshot |
| RF-03 | Re-point the head at the new snapshot | Must | `head.predecessor_id == snapshot.id` |
| RF-04 | Give the snapshot the head's previous predecessor | Must | `snapshot.predecessor_id == old head.predecessor_id` |
| RF-05 | Keep the snapshot on the head's branch | Must | `snapshot.branch_id == head.branch_id` |
| RF-06 | Resolve the lineage root when the head is the root | Must | Snapshotting the root yields `snapshot.root_id == root.id` |
| RF-07 | Refuse to snapshot an immutable node | Must | → 422 with the documented message |
| RF-08 | Carry `label`, `note` and `provenance_message_id` | Must | All three readable on the returned `VersionNode`; `label` is required (`min_length=1`) |
| RF-09 | Fork an editable branch from an immutable node | Must | `POST /aeroplanes/{snapshot_id}/restore` → **201** `BranchOut` |
| RF-10 | Refuse to restore from a mutable node | Must | → 422 |
| RF-11 | Default the restore branch name | Must | `restore/<label>`, or `restore/<node_id>` when unlabelled; an explicit name wins |
| RF-12 | Take an automatic snapshot before a destructive spar edit | Must | A segment split or spare REPLACE is preceded by a `"Before spar insert"` snapshot |
| RF-13 | Abort the destructive edit if the snapshot fails | Must | With `snapshot` patched to raise, **no** mutation is performed |
| RF-14 | Return the snapshot id to the caller of a destructive edit | Should | `SparInsertResponse` carries it for one-click revert |
| RF-15 | Run inside the caller's transaction | Must | A rollback after the snapshot leaves neither the snapshot nor the re-pointed head |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Correctness | The head's identity survives a snapshot, so no inbound reference is invalidated | `snapshot:150-183`; BR-38 | 🟢 |
| Correctness | The predecessor chain stays linear because the snapshot inherits the head's old predecessor | `:164` | 🟢 |
| Correctness | The root case is handled explicitly rather than by relying on a nullable `root_id` | `:156` | 🟢 |
| Safety | A destructive edit cannot proceed without a recovery point — the failure aborts the commit, it does not warn | `spar_insert_service.py:485-497`; BR-41 | 🟢 |
| Reliability | The two flushes are ordered so the head can never point at an unflushed row | `:174-178` | 🟢 |
| Reliability | Everything runs in the request transaction (ADR 0009) | module docstring | 🟢 |
| Observability | `logger.info("snapshot: node %s → snapshot %s (label=%r)")` on every snapshot | `:180-182` | 🟢 |
| Integrity | Immutability is a **checked convention**, not a database constraint — nothing stops a direct write to a frozen node | `_guard_immutable` applied only on `snapshot` | 🟡 |
| Scalability | Every snapshot is a full subgraph copy, with no retention policy | `clone_aeroplane_subgraph` | 🟡 |

## Acceptance Criteria

```gherkin
Feature: Snapshot topology

  Scenario: The snapshot is inserted behind the head
    Given a mutable head H whose predecessor is P
    When I snapshot H with label "before spar"
    Then a new node S exists with is_immutable true
    And S.predecessor_id is P
    And H.predecessor_id is S
    And H.id and H.uuid are unchanged
    And S.branch_id equals H.branch_id

  Scenario: Snapshotting the lineage root
    Given a lineage root whose root_id is null
    When I snapshot it
    Then the snapshot's root_id is the root's own id
    And the snapshot appears in the lineage tree

  Scenario: The label, note and provenance cursor are carried
    When I snapshot with label "L", note "N" and provenance_message_id 42
    Then the returned node has version_label "L", version_note "N"
      and provenance_message_id 42

  Scenario: A label is required
    When I POST a snapshot with an empty label
    Then the response status is 422

  Scenario: An immutable node cannot be snapshotted
    Given an immutable snapshot node
    When I POST /aeroplanes/{id}/snapshot
    Then the response status is 422
    And the message says the node cannot be mutated

Feature: Restore

  Scenario: Restoring from a snapshot creates a mutable head
    Given an immutable snapshot S
    When I POST /aeroplanes/{S}/restore
    Then the response status is 201
    And a new branch exists whose head is mutable
    And that head's predecessor_id is S

  Scenario: Restoring from a mutable node is refused
    Given a mutable head
    When I POST /aeroplanes/{id}/restore
    Then the response status is 422

  Scenario: The branch name defaults from the label
    Given an immutable snapshot labelled "before spar"
    When I restore it without a name
    Then the new branch is named "restore/before spar"

  Scenario: An unlabelled snapshot falls back to its id
    Given an immutable snapshot with no version_label and id 17
    When I restore it without a name
    Then the new branch is named "restore/17"

  Scenario: An explicit name wins
    When I restore with name "recovery"
    Then the branch is named "recovery"

Feature: Recovery point before a destructive edit

  Scenario: A destructive spar commit snapshots first
    Given an aircraft with a spar plan requiring a segment split
    When I commit the spar insert
    Then an immutable snapshot labelled "Before spar insert" exists
    And its id is returned in the response

  Scenario: A failing snapshot aborts the whole commit
    Given aeroplane_version_service.snapshot raises
    When I commit a destructive spar insert
    Then the commit fails
    And no wing geometry has been modified

Feature: Transaction discipline

  Scenario: A rollback undoes the snapshot and the re-point
    Given a snapshot has been taken inside a request
    When the request raises before commit
    Then no snapshot row exists
    And the head's predecessor_id is unchanged
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Insert-behind topology + identity preservation (RF-01…RF-05) | Must | The entire design rests on it; getting it backwards invalidates every reference to the head |
| Root resolution (RF-06) | Must | Without it, a snapshot of the lineage root disappears from the version graph |
| Both immutability guards (RF-07/RF-10) | Must | The two halves of BR-37; each protects a different direction |
| Label / note / provenance carriage (RF-08) | Must | A snapshot without a label is unidentifiable in the UI list |
| Restore (RF-09/RF-11) | Must | The undo path; the default name is what makes a restored branch recognisable |
| Automatic pre-mutation snapshot + abort (RF-12/RF-13) | Must | BR-41 — a destructive edit without a recovery point is unrecoverable |
| Transaction discipline (RF-15) | Must | ADR 0009 |
| Returning the snapshot id (RF-14) | Should | Enables one-click revert; the snapshot exists either way |
| Enforcing immutability at the database level | Won't | 🟡 not implemented — only `snapshot` checks |
| Snapshot retention / pruning | Won't | 🟡 not implemented |
| `preview_png` thumbnails | Won't | 🟡 the column exists and is never written |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/models/aeroplanemodel.py:662-716` | `is_immutable`, `version_label`, `version_note`, `provenance_message_id`, `preview_png` | 🟢 |
| `app/services/aeroplane_version_service.py:65-71` | `_guard_immutable` | 🟢 |
| `…:125-183` | `snapshot` | 🟢 |
| `…:291-321` | `restore` | 🟢 |
| `app/services/aeroplane_clone_service.py:184-206` | the clone's `immutable` flag and nulled version metadata | 🟢 |
| `app/services/spar_insert_service.py:485-497` | the automatic pre-mutation snapshot (gh-1058) | 🟢 owned by `wing-design` |
| `app/api/v2/endpoints/versioning.py:111-141, 185-211` | the snapshot and restore routes | 🟢 |
| `app/schemas/versioning.py` | `SnapshotRequest`, `VersionNode` | 🟢 |
| `_reversa_sdd/state-machines.md` §6 | the node state machine | 🟢 |
</content>
