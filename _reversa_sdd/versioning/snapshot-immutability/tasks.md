# snapshot-immutability — Implementation Tasks

> Executable sequence to re-implement the use case from the legacy behaviour.
> Every task cites the legacy file, a definition of done, and a confidence
> marker. Parent module tasks: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] `aeroplanes` with `is_immutable` (NOT NULL, `server_default="false"`),
      `version_label`, `version_note`, `provenance_message_id`, `preview_png` —
      see [`../tasks.md`](../tasks.md) T-02.
- [ ] `clone_aeroplane_subgraph` accepting `immutable`, `branch_id`,
      `predecessor_id` and `root_id` — see
      [`../aeroplane-clone-subgraph/tasks.md`](../aeroplane-clone-subgraph/tasks.md).
- [ ] `create_branch` — see
      [`../branch-model/tasks.md`](../branch-model/tasks.md) T-03. `restore`
      delegates to it.
- [ ] `get_db()` request-scoped session (ADR 0009). Nothing here commits.
- [ ] `copilot_messages` table (for the `provenance_message_id` FK) — module
      `ai-copilot`. May be empty.

## Tasks

- [ ] **T-01 — `_guard_immutable`.**
  `if node.is_immutable: raise ValidationError("Cannot mutate an immutable
  snapshot node", details={"node_id": node.id, "is_immutable": True})`.
  - Legacy origin: `app/services/aeroplane_version_service.py:65-71`
  - Definition of done: the message and both `details` keys are reproduced
    verbatim — the UI keys off them.
  - Confidence: 🟢

- [ ] **T-02 — `snapshot` — the topology.**
  Guard; `resolved_root_id = head.root_id if head.root_id is not None else
  head.id`; clone with `immutable=True`, `branch_id=head.branch_id`,
  `predecessor_id=head.predecessor_id`; assign `version_label`,
  `version_note`, `provenance_message_id`, `created_by="human"`; **flush**;
  set `head.predecessor_id = snapshot_node.id`; **flush**; log.
  - Legacy origin: `app/services/aeroplane_version_service.py:125-183`
  - Definition of done: **four** assertions in one test — `S.predecessor_id ==
    old P`, `H.predecessor_id == S`, `H.id` and `H.uuid` unchanged, and
    `S.branch_id == H.branch_id`. A variant that reads
    `head.predecessor_id` *after* the re-point must fail.
  - Confidence: 🟢

- [ ] **T-03 — Root resolution.**
  A head whose `root_id` is `NULL` (the lineage root) yields a snapshot with
  `root_id = head.id`.
  - Legacy origin: `app/services/aeroplane_version_service.py:153-156`
  - Definition of done: snapshotting the root produces a node that **appears in
    `list_tree`** — the test asserts the tree membership, not just the column,
    because that is the failure this line prevents.
  - Confidence: 🟢

- [ ] **T-04 — The two flushes, in order.**
  ① after assigning the metadata (obtains `snapshot_node.id`); ② after
  re-pointing the head.
  - Legacy origin: `app/services/aeroplane_version_service.py:174-178`
  - Definition of done: a variant that re-points the head before the first
    flush leaves `head.predecessor_id` `None` — the test proves the order
    matters.
  - Confidence: 🟢

- [ ] **T-05 — `restore` with the mirror guard.**
  `not node.is_immutable` ⇒ `ValidationError("restore() requires an immutable
  snapshot node", details={node_id, is_immutable: False})`; then
  `branch_name = name or f"restore/{node.version_label or snapshot_node_id}"`;
  delegate to `create_branch`.
  - Legacy origin: `app/services/aeroplane_version_service.py:291-321`
  - Definition of done: three name cases (explicit · labelled · unlabelled) and
    the 422 on a mutable node; the resulting head is **mutable** with
    `predecessor_id = snapshot_node_id`.
  - Confidence: 🟢

- [ ] **T-06 — `SnapshotRequest` and the snapshot route.**
  `SnapshotRequest{label (min_length=1), note?, provenance_message_id?}` with
  `extra="forbid"`; `POST /aeroplanes/{aeroplane_id}/snapshot`, **201**,
  `operation_id=snapshot_aeroplane`, path typed `int`, returning the **snapshot**
  node as a `VersionNode`.
  - Legacy origin: `app/api/v2/endpoints/versioning.py:111-141`,
    `app/schemas/versioning.py`
  - Definition of done: an empty label is 422 (from Pydantic); an unknown field
    is 422 (`extra="forbid"`); the response is the snapshot, **not** the head.
  - Confidence: 🟢

- [ ] **T-07 — The restore route.**
  `POST /aeroplanes/{snapshot_id}/restore`, **201**,
  `operation_id=restore_snapshot`, body `BranchRequest`, returning `BranchOut`.
  - Legacy origin: `app/api/v2/endpoints/versioning.py:185-211`
  - Definition of done: 201 on an immutable node, 422 on a mutable one, 404 on
    an unknown id.
  - Confidence: 🟢

- [ ] **T-08 — The automatic pre-mutation snapshot (gh-1058).**
  In `spar_insert_service`, a **destructive** commit (segment split or spare
  REPLACE) calls `snapshot(..., label="Before spar insert")` **before** any
  mutation, aborts the whole commit if it raises, and returns the snapshot id in
  `SparInsertResponse`.
  - Legacy origin: `app/services/spar_insert_service.py:485-497`
  - Definition of done: with `snapshot` patched to raise, the commit fails and
    **no wing geometry is modified** — assert the geometry, not just the
    exception. This is the whole point of BR-41.
  - Confidence: 🟢 · owned by `wing-design`; verify from this side too.

- [ ] **T-09 — Characterise the unguarded mutation path.**
  `_guard_immutable` is applied **only** inside `snapshot`; an ordinary
  geometry write addressed at a snapshot's UUID is not blocked.
  - Legacy origin: the absence of a guard in `wing_service`, `fuselage_service`,
    `component_tree_service`, …
  - Definition of done: a test performs a wing edit on an immutable node and
    asserts it **succeeds** today, with a docstring naming the gap. Do not add
    the guard here — that is a product decision (see Pending Gaps).
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Topology:** the four assertions of T-02, plus a case where the
      head has no predecessor (the snapshot becomes the tail).
- [ ] **TT-02 — Root snapshot:** appears in `list_tree`.
- [ ] **TT-03 — Guards:** snapshot of an immutable node ⇒ 422 with the exact
      message; restore of a mutable node ⇒ 422.
- [ ] **TT-04 — Metadata carriage:** `label`, `note` and
      `provenance_message_id` are readable on the returned node; the clone
      itself nulls all five version columns before `snapshot` assigns four.
- [ ] **TT-05 — Empty label:** 422 from the request schema; unknown field 422
      from `extra="forbid"`.
- [ ] **TT-06 — Restore names:** explicit · `restore/<label>` ·
      `restore/<id>`.
- [ ] **TT-07 — Restore output:** a **mutable** head whose `predecessor_id` is
      the snapshot, on a new branch.
- [ ] **TT-08 — Double restore (characterisation):** restoring the same snapshot
      twice yields two branches with the **same** name.
- [ ] **TT-09 — Flush order:** re-pointing before the first flush leaves the
      head pointing at `None`.
- [ ] **TT-10 — Transaction:** a rollback after a snapshot leaves neither the
      snapshot row nor the head's re-pointing.
- [ ] **TT-11 — Spar abort:** patched `snapshot` ⇒ no geometry change.
- [ ] **TT-12 — Snapshot id returned** in `SparInsertResponse`.
- [ ] **TT-13 — Unguarded mutation (characterisation):** a wing edit on an
      immutable node succeeds today.
- [ ] **TT-14 — Logging:** `snapshot` emits `logger.info` naming the head id,
      the snapshot id and the label.
- [ ] **TT-15 — `created_by` (characterisation):** a snapshot taken through the
      copilot path still records `"human"`.

## Data Migration Tasks

- [ ] **TM-01 — `is_immutable` defaults to `false` on every backfilled row.**
      The gh-903 migration sets it explicitly (`UPDATE aeroplanes SET … 
      is_immutable = 0`) rather than relying on the server default, so
      pre-versioning rows are unambiguously mutable. 🟢
- [ ] **TM-02 — No snapshot was back-migrated.** The retired `design_versions`
      table was dropped and its downgrade recreates it **empty** — historical
      JSON snapshots do not exist as nodes. Say so in the migration docstring.
      🟢
- [ ] **TM-03 — `preview_png` stays NULL.** Nothing writes it; do not backfill
      a placeholder. 🔴 pending the product decision below.

## Suggested Order

1. **T-01** first — the guard is three lines and is the precondition for T-02's
   first branch.
2. **T-02 → T-04** as one unit: the topology, the root resolution and the flush
   order are the use case. Each has a dedicated failure test, and all three are
   the kind of detail a well-meaning refactor breaks silently.
3. **T-05** next — `restore` is a guard plus a name, delegating to
   `create_branch`, so it is cheap once T-02 is proven.
4. **T-06 → T-07** the two routes and the request schema.
5. **T-08** once `snapshot` is stable: the spar abort is an integration
   behaviour and only means something against a working snapshot.
6. **T-09** last — it is a characterisation of what is *missing*, and writing it
   earlier would invite "fixing" the gap before the product decision is made.

## Pending Gaps

- **Should immutability be enforced beyond `snapshot`?** Today nothing prevents
  a geometry write addressed at a frozen node — no constraint, no ORM event, no
  service guard. Options: a `before_flush` ORM event, a guard in every mutating
  service, or a database trigger.
- **Is there a retention policy for snapshots?** Every one is a full subgraph
  copy and `spar_insert_service` takes them automatically on every destructive
  commit. Nothing prunes, counts or measures them.
- **Should `created_by` on a snapshot reflect the caller** rather than always
  being `"human"`? A copilot-triggered snapshot and a user-taken one are
  currently indistinguishable.
- **Should `provenance_message_id` be readable?** It is accepted, stored,
  returned — and no route, tool or query resolves it back to the conversation
  turn.
- **Should `preview_png` be generated**, or should the column be dropped?
- **Should restoring the same snapshot twice be prevented**, or at least
  produce distinct branch names?
- **Should `restore` log?** Today it is invisible in the logs except as an
  ordinary `create_branch`.
