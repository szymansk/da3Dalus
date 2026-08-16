# snapshot-immutability — Technical Design

> Use-case design, nested under the module [`versioning`](../design.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Full endpoint contract: [`../contracts.md`](../contracts.md).

## Interface

### State 🟢

| Column | Type | Meaning |
|---|---|---|
| `is_immutable` | Boolean NOT NULL, `server_default="false"` | `True` = frozen snapshot; `False` = editable head |
| `version_label` | String? | e.g. `"Before spar insert"` — required by the request schema |
| `version_note` | Text? | why the snapshot was taken |
| `provenance_message_id` | Integer? FK → `copilot_messages.id` | the AI cursor; **write-only** 🟡 |
| `preview_png` | Text? | base64 thumbnail — **never written** 🟡 (`Q-VS-2`) |

There are exactly **two** node states. `state-machines.md` §6 derives a third
*presentation* state (`is_head`) from `branches.head_id`, but that is a computed
flag, not a column.

### Functions 🟢

| Symbol | Signature | Line |
|---|---|---|
| `_guard_immutable` | `(node) -> None` | 65 |
| `snapshot` | `(db, node_id, label, note=None, provenance_message_id=None) -> AeroplaneModel` | 125 |
| `restore` | `(db, snapshot_node_id, name=None, created_by="human") -> BranchModel` | 291 |

### REST 🟢

| Method | Path | Returns | Status |
|---|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/snapshot` | `VersionNode` (the **snapshot**) | **201** · 404 · 409 · 422 |
| POST | `/aeroplanes/{snapshot_id}/restore` | `BranchOut` | **201** · 404 · 422 |

## Main Flow

### F1 — The topology 🟢

```
before:   [old_pred] ← [head (mutable, id=H)]
after:    [old_pred] ← [snapshot (immutable, id=S)] ← [head (id=H, unchanged)]
```

This is the design's central, counter-intuitive choice. The obvious alternative
— freeze the head in place and create a new editable copy — would change the id
of the *live* aircraft, invalidating every URL, every foreign key and every
open browser tab. Inserting the frozen copy **behind** the head means the live
node is untouched. 🟢

### F2 — `snapshot` (l.125-183) 🟢

```
head = _get_node(db, node_id)
_guard_immutable(head)                     # already frozen -> ValidationError (422)

resolved_root_id = head.root_id if head.root_id is not None else head.id

snapshot_node = clone_aeroplane_subgraph(
        db, head,
        immutable=True,
        branch_id=head.branch_id,          # stays on the head's branch
        predecessor_id=head.predecessor_id,# inherits the head's OLD predecessor
        root_id=resolved_root_id)

snapshot_node.version_label         = label
snapshot_node.version_note          = note
snapshot_node.provenance_message_id = provenance_message_id
snapshot_node.created_by            = "human"      # HARD-CODED 🔴

db.flush()                                 # ① snapshot_node.id now exists

head.predecessor_id = snapshot_node.id     # ② re-point the head
db.flush()

logger.info("snapshot: node %s → snapshot %s (label=%r)", head.id,
            snapshot_node.id, label)
return snapshot_node
```

Four details that a re-implementation must not "tidy":

1. **`resolved_root_id`** — the lineage root's own `root_id` may be `NULL`; a
   snapshot carrying `NULL` would be invisible to `list_tree`
   ([`../branch-model/design.md`](../branch-model/design.md) BR-BM6).
2. **`predecessor_id=head.predecessor_id`** is read **before** the head is
   re-pointed, which is what keeps the chain linear rather than circular.
3. **The two flushes are ordered.** Without ① the snapshot has no id to point
   at.
4. **`created_by = "human"`** is unconditional — see
   [`../copilot-provenance/design.md`](../copilot-provenance/design.md).

### F3 — `restore` (l.291-321) 🟢

```
node = _get_node(db, snapshot_node_id)
if not node.is_immutable:
    raise ValidationError("restore() requires an immutable snapshot node",
                          details={node_id, is_immutable: False})

branch_name = name or f"restore/{node.version_label or snapshot_node_id}"
return create_branch(db, from_node_id=snapshot_node_id,
                     name=branch_name, created_by=created_by)
```

The guard is the **mirror** of `_guard_immutable`: `snapshot` refuses a frozen
node, `restore` requires one. Everything after the guard is
[`branch-model`](../branch-model/design.md)'s `create_branch`, which produces a
**mutable** clone whose `predecessor_id` is the snapshot. 🟢

The name fallback chain is `explicit name → "restore/<label>" →
"restore/<id>"`. 🟢

### F4 — The automatic recovery point (gh-1058) 🟢

```
spar_insert_service, on a DESTRUCTIVE commit (segment split or spare REPLACE):

    snapshot_id = aeroplane_version_service.snapshot(
                      db, node_id, label="Before spar insert", …)
    # if this raises, the WHOLE commit aborts — nothing is mutated
    … perform the destructive edit …
    return SparInsertResponse(..., snapshot_id=snapshot_id)
```

The abort is the point. A warning would leave the user with a mutated aircraft
and no way back; the code chooses to fail the operation instead
(`spar_insert_service.py:485-497`, *"never mutate without a recovery point"*).
🟢

## Alternative Flows

- **Snapshot of an already-immutable node:** `ValidationError` → **422** with
  `node_id` and `is_immutable` in `details`. 🟢
- **Snapshot of the lineage root:** `resolved_root_id` falls back to
  `head.id`. 🟢
- **Snapshot of a head with no predecessor:** the snapshot's
  `predecessor_id` is `None` — it becomes the chain's new tail. 🟢
- **Empty `label`:** rejected by `SnapshotRequest` (`min_length=1`) before the
  service runs — a Pydantic 422, not the service's. 🟡 Two 422 shapes.
- **`provenance_message_id` pointing at a non-existent message:** the FK is
  `use_alter`; whether it is enforced depends on the backend's FK enforcement.
  🟡 Not validated in the service.
- **Restore from a mutable node:** `ValidationError` → 422. 🟢
- **Restore of an unlabelled snapshot without a name:** `restore/<node_id>`. 🟢
- **Restore colliding with an existing branch name:** allowed —
  `create_branch` performs no collision check
  ([`../branch-model`](../branch-model/design.md) BR-42). 🔴 Restoring the same
  snapshot twice yields two branches with the same name.
- **A direct write to an immutable node** (e.g. `PUT /aeroplanes/{uuid}/wings/…`
  addressed at a snapshot's UUID): **nothing stops it**. `_guard_immutable` is
  applied only inside `snapshot`. 🔴
- **The spar snapshot fails:** the commit aborts and no geometry is touched. 🟢
- **A rollback after a snapshot:** both the snapshot row and the head's
  re-pointing disappear together (ADR 0009). 🟢

## Dependencies

- **[`aeroplane-clone-subgraph`](../aeroplane-clone-subgraph/design.md)** — the
  frozen copy is a full subgraph clone; `snapshot` only sets four columns
  afterwards.
- **[`branch-model`](../branch-model/design.md)** — `restore` delegates to
  `create_branch`; a snapshot lives on the head's branch and is therefore
  deleted with it by `discard_branch`.
- **[`copilot-provenance`](../copilot-provenance/design.md)** — the
  `provenance_message_id` cursor and the hard-coded `created_by`.
- **`wing-design` (`spar_insert_service`)** — the only non-copilot automated
  caller, and the one that turns BR-41 into an enforced rule.
- **`app/db/session.py` (`get_db`)** — the transaction (ADR 0009).

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| A snapshot is inserted behind the head so the live node keeps its identity | `snapshot:150-183`; BR-38 | 🟢 |
| The snapshot inherits the head's old predecessor, keeping the chain linear | `:164` | 🟢 |
| The root case is resolved explicitly rather than relying on a nullable `root_id` | `:156` | 🟢 |
| A snapshot stays on the head's branch rather than getting one of its own | `:162` | 🟢 |
| `snapshot` and `restore` carry mirror-image guards | `_guard_immutable` vs `restore:314-318` | 🟢 |
| Version metadata is assigned after the clone, which always nulls it | `:169-172` vs clone `:198-200` | 🟢 |
| `created_by` on a snapshot is unconditionally `"human"` | `:172` | 🟢 (🟢 `created_by` is fixed to the canonical `human` | `ai` vocabulary with a DB CHECK (`Q-CC-9`, maintainer-answered); agent detail moves to a separate field.) |
| The restore branch name is derived from the snapshot's label | `:320` | 🟢 |
| A destructive edit **aborts** rather than warns when its recovery point fails | `spar_insert_service.py:485-497`; gh-1058 | 🟢 |
| 🟡 Immutability is enforced in the write-resolver plus a session-level check (`Q-VS-1`); a **database** constraint is deferred to the PostgreSQL decision (`R2-07`, `Q-CC-7`). Direct SQL bypasses it — stated as a declared boundary, like the component-tree cascade in `Q-AC-10` | only `snapshot` guards | 🟢 (a 🔴 gap) |

## Internal State

```
        create_aeroplane
              │
              ▼
      ┌──────────────┐   snapshot()  ┌────────────────────┐
      │ MutableHead  │──────────────▶│ ImmutableSnapshot  │
      │ is_immutable │  (a NEW node  │ is_immutable=True  │
      │   = False    │   inserted    │                    │
      └──────────────┘   BEHIND it)  └────────────────────┘
              ▲                                │
              │        restore(name)           │
              └────────────────────────────────┘
                  (clone into a NEW branch head)

      discard_branch() deletes nodes of BOTH states, guarded
```

The transition is **not** in place: `snapshot()` never changes the head's
`is_immutable` — it creates a second node. A node's `is_immutable` value is
therefore fixed at creation and never updated anywhere in the module. 🟢

## Observability

- `logger.info("snapshot: node %s → snapshot %s (label=%r)")` on every
  snapshot — the id mapping needed to reconstruct a lineage from logs. 🟢
- `restore` has **no** log line of its own; the delegated `create_branch` logs
  instead, so a restore appears in the log as a plain branch creation. 🟡
- The router's `_call` catch-all does not log. 🔴
- Nothing counts snapshots per lineage or measures their storage, despite every
  one being a full subgraph copy and `spar_insert_service` taking them
  automatically. 🔴

## Risks and Gaps

- 🔴 **Immutability is not enforced outside `snapshot`.** No database
  constraint, ORM event or service guard prevents a wing edit addressed at a
  snapshot's UUID from mutating a "frozen" node — the guarantee is a convention
  that only one code path checks.
- 🔴 **No storage-growth control.** Every snapshot copies the whole design
  subgraph, `spar_insert_service` snapshots automatically on every destructive
  commit, and there is no retention policy, prune or size accounting.
- 🔴 **`created_by` on a snapshot is always `"human"`**, so a copilot-triggered
  or automatic snapshot is indistinguishable from a user-taken one.
- 🔴 **`provenance_message_id` is write-only** — nothing resolves a snapshot
  back to the conversation turn that produced it.
- 🟡 **`preview_png`** — the column, the clone reset and the `VersionNode` field all exist; no code path generates a thumbnail (`Q-VS-2`). is never written**, so the version list has no visual
  differentiator.
- 🔴 **Restoring the same snapshot twice produces two identically named
  branches**, because `create_branch` performs no collision check.
- 🟡 **`restore` does not log**, so a restore is indistinguishable from an
  ordinary branch creation in the logs.
- 🟡 **The empty-label rejection comes from Pydantic**, producing a different
  422 body shape than the service's guards.
- 🟡 **`provenance_message_id` is not validated** in the service; enforcement
  depends on the backend's FK behaviour.
