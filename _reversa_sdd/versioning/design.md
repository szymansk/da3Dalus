# versioning — Technical Design

> Module-level design. Focuses on HOW the module is built, derived from the
> legacy code. Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Endpoint contract: [`contracts.md`](contracts.md).
> Use cases: [`branch-model`](branch-model/design.md) ·
> [`snapshot-immutability`](snapshot-immutability/design.md) ·
> [`aeroplane-clone-subgraph`](aeroplane-clone-subgraph/design.md) ·
> [`copilot-provenance`](copilot-provenance/design.md).

## Interface

### Persistence 🟢

**`branches`**

| Column | Type | Req. | Default | Note |
|---|---|---|---|---|
| `root_id` | Integer FK → `aeroplanes.id` (`use_alter`) | yes | — | the lineage root |
| `head_id` | Integer FK → `aeroplanes.id` (`use_alter`) | yes | — | the currently mutable node |
| `name` | String | yes | — | `"main"`, `"copilot-proposal-<msg>"`, `"restore/<label>"`; **no DB uniqueness** |
| `is_main` | Boolean | yes | `False` (`server_default="false"`) | exactly one `True` per `root_id` |
| `created_by` | String | no | `NULL` | `'human'` / `'ai'` / `'copilot'` — no enum 🟡 |
| `created_at` | DateTime(tz) | yes | `func.now()` | |

Partial unique index `uq_branches_one_main_per_root ON branches(root_id) WHERE
is_main`, declared identically in the model and the migration. Relationships use
explicit `foreign_keys=` to disambiguate the two FKs into `aeroplanes`.

**Versioning columns on `aeroplanes`** — `branch_id`, `predecessor_id`,
`root_id`, `is_immutable` (NOT NULL, `server_default="false"`),
`version_label`, `version_note`, `created_by`, `provenance_message_id`,
`preview_png`. All FKs `use_alter=True`.

### Service — `aeroplane_version_service.py` 🟢

| Symbol | Line | Raises |
|---|---|---|
| `_get_node(db, id)` | 41 | `NotFoundError("Aeroplane not found")` |
| `_get_node_by_uuid(db, uuid)` | 49 | 🟡 dead — no caller |
| `_get_branch(db, id)` | 57 | `NotFoundError("Branch not found")` |
| `_guard_immutable(node)` | 65 | `ValidationError("Cannot mutate an immutable snapshot node")` |
| `_metrics_payload(node)` | 74 | — |
| `snapshot(db, node_id, label, note, provenance_message_id)` | 125 | `NotFound`, `Validation` |
| `create_branch(db, from_node_id, name, created_by)` | 186 | `NotFound` |
| `adopt_branch(db, branch_id)` | 244 | `NotFound`, `Conflict` |
| `restore(db, snapshot_node_id, name, created_by)` | 291 | `NotFound`, `Validation` |
| `discard_branch(db, branch_id)` | 324 | `NotFound`, `Conflict` |
| `compare(db, a, b)` | 396 | `NotFound` |
| `list_tree(db, root_id)` | 415 | `NotFound` |
| `rename_branch(db, branch_id, name)` | 459 | `NotFound`, `Validation`, `Conflict` |
| `list_aeroplanes_heads_only(db)` | 515 | — |

### Clone — `aeroplane_clone_service.py` 🟢

`clone_aeroplane_subgraph(db, source, *, immutable, branch_id, predecessor_id,
root_id) -> AeroplaneModel`, plus `_remap_component_overrides` and
`_clone_component_tree`, and the two registry constants.

### REST 🟢

8 routes, **all integer-PK addressed** — see [`contracts.md`](contracts.md).

## Main Flow

### F1 — The DAG 🟢

```
root_id         → the lineage root; the ROOT POINTS AT ITSELF
predecessor_id  → self-referential; what this node was forked from
branch_id       → which branch owns this node
is_immutable    → frozen snapshot vs editable head
```

A lineage is therefore *all rows sharing a `root_id`* (plus the root itself),
and a branch is a named pointer to one mutable head within it. 🟢

### F2 — Snapshot (l.125-183) 🟢

```
head = _get_node(db, node_id) ; _guard_immutable(head)
resolved_root_id = head.root_id if head.root_id is not None else head.id

snapshot_node = clone_aeroplane_subgraph(
        db, head,
        immutable=True,
        branch_id=head.branch_id,              # same branch
        predecessor_id=head.predecessor_id,    # inherits the head's OLD predecessor
        root_id=resolved_root_id)

snapshot_node.version_label = label
snapshot_node.version_note  = note
snapshot_node.provenance_message_id = provenance_message_id
snapshot_node.created_by = "human"             # HARD-CODED 🔴
db.flush()                                     # obtain snapshot_node.id

head.predecessor_id = snapshot_node.id         # re-point the head
db.flush()
```

The counter-intuitive part is deliberate: the **head keeps its identity** and
the frozen copy is inserted *behind* it, so nothing that references the head has
to be re-pointed. See
[`snapshot-immutability`](snapshot-immutability/design.md). 🟢

### F3 — Create branch (l.186-241) 🟢

```
source  = _get_node(db, from_node_id)          # head OR snapshot — no guard
root_id = source.root_id or source.id

new_head = clone_aeroplane_subgraph(db, source, immutable=False,
                                    branch_id=None,          # not known yet
                                    predecessor_id=source.id,
                                    root_id=root_id)
new_head.created_by = created_by ; db.flush()  # obtain new_head.id

branch = BranchModel(root_id, head_id=new_head.id, name, is_main=False,
                     created_by)
db.add(branch) ; db.flush()                    # obtain branch.id

new_head.branch_id = branch.id ; db.flush()    # back-fill
```

The three-flush dance mirrors `create_aeroplane`'s and exists for the same
reason: the circular FK pair cannot be satisfied in one statement. 🟢
**No name-collision check — 🟢 `create_branch` now enforces uniqueness per `root_id` (`R2-04`), raising `ConflictError` → 409. Unlike `aeroplanes.name` (`Q-AC-2`, duplicated **by construction** because every snapshot copies it), a branch name is a user-chosen label that nothing duplicates automatically — and it is how a human finds a branch, since the UUID is neither visible nor memorable.

### F4 — Adopt (l.244-288) 🟢

```
branch = _get_branch(db, branch_id)
branch.is_main -> ConflictError (409)

current_main = branches WHERE root_id = branch.root_id AND is_main = True
current_main.is_main = False ; db.flush()      # DEMOTE FIRST — the partial index
branch.is_main = True ; db.flush()
```

Reversing the order makes the partial unique index reject the write; the comment
at `:277` says so. 🟢

### F5 — Restore (l.291-321) 🟢

```
node = _get_node(db, snapshot_node_id)
not node.is_immutable -> ValidationError (422)   # the MIRROR of _guard_immutable
branch_name = name or f"restore/{node.version_label or snapshot_node_id}"
return create_branch(db, from_node_id=snapshot_node_id, name=branch_name, ...)
```

Restore is `create_branch` with an immutability *requirement* — forking from a
live head is already `create_branch`, so restoring from one would be
meaningless. 🟢

### F6 — Discard (l.324-393) 🟢

```
1. branch.is_main                          -> ConflictError (409)
   COUNT(branches WHERE root_id = ?) <= 1  -> ConflictError (409)
2. nodes = aeroplanes WHERE branch_id = ?
3. UPDATE aeroplanes SET predecessor_id = NULL
   WHERE predecessor_id IN {node ids}      # SQLite has no deferrable FKs
4. db.delete(branch) ; db.flush()          # BEFORE the nodes, or SQLAlchemy
                                           # nulls branches.head_id (NOT NULL)
5. for node in nodes: db.delete(node)      # ORM cascade removes the subgraph
   db.flush()
```

Every step is load-bearing and the code comments say why. 🟢

### F7 — Read paths 🟢

```
list_tree(root_id):
    _get_node(db, root_id)                 # 404 if the root is unknown
    nodes    = aeroplanes WHERE id = root_id OR root_id = root_id   ORDER BY id
    branches = branches   WHERE root_id = root_id                   ORDER BY id
    → the endpoint computes is_head = node.id in {b.head_id}

compare(a, b):
    return node_a, node_b, _metrics_payload(node_a), _metrics_payload(node_b)

list_aeroplanes_heads_only():
    aeroplanes WHERE branch_id IS NULL          # legacy rows stay visible
                  OR id IN (SELECT head_id FROM branches)
    ORDER BY name
```

`_metrics_payload` (l.74-117) returns `id`, `uuid`, `name`, `total_mass_kg`, the
whole `assumption_computation_context` when non-empty, `wing_count`,
`wing_names[]` (gh-938 — so the copilot targets a wing by **name**), `wings[]`
with `n_xsecs` (gh-938 Bug A — `at_index = n_xsecs` appends at the tip),
`fuselage_count`, and `stability` from `stability_results[-1]` — the **last**
row, not the newest by timestamp. 🔴

### F8 — The clone 🟢

Ten ordered groups with a `flush()` after each, so auto-generated PKs are
available for re-keying:

```
1  aeroplanes            new uuid4; name / total_mass_kg / xyz_ref /
                         assumption_computation_context deep-copied;
                         flight_profile_id KEPT; version metadata = None
2  weight_items          + weight_id_map: str(old id) → str(new id)
3  wings → wing_xsecs → wing_xsec_details
     → spares · turbulator (1:1, gh-1069) · TED → ted_servo
       (servo.component_id KEPT)
4  fuselages → fuselage_xsecs        step_path / solid_step_path → NULL
5  mission_objective     (1:1)
6  design_assumptions    estimate + calculated + active_source + divergence
7  aircraft_computation_config (1:1)
8  stability_results     including computed_at and geometry_hash
9  loading_scenarios     component_overrides REMAPPED via weight_id_map
10 component_tree        aeroplane_id = str(clone.uuid); parent_id remapped
```

Detail in [`aeroplane-clone-subgraph`](aeroplane-clone-subgraph/design.md). 🟢

## Alternative Flows

- **Snapshot of an immutable node:** 422. 🟢
- **Snapshot of the lineage root** (whose `root_id` may be `NULL`): resolved via
  `head.root_id or head.id`. 🟢
- **Branch from a snapshot:** allowed — `create_branch` has no immutability
  guard, which is exactly what makes `restore` a thin wrapper. 🟢
- **Adopt an already-main branch:** 409. 🟢
- **Adopt when no current main exists** (a legacy lineage): the demote step is
  skipped (`current_main is None`) and the promotion proceeds. 🟡
- **Restore from a mutable node:** 422. 🟢
- **Restore without a name:** `restore/<version_label>`, or `restore/<node_id>`
  when the snapshot has no label. 🟢
- **Discard the main or only branch:** 409. 🟢
- **Discard a branch whose nodes are other nodes' predecessors:** those links
  are nulled (step 3), silently truncating the survivors' lineage. 🔴
- **Rename to a colliding name:** 409. **Create** with a colliding name:
  allowed. 🔴
- **`list_tree` for a node whose `root_id` is `NULL`:** invisible in the
  graph. 🔴
- **`compare` of two nodes in different lineages:** allowed; nothing checks
  that `a` and `b` share a root. 🟡
- **Unknown node/branch id anywhere:** 404 with `{"detail": …}`. 🟢
- **Any other exception:** the router's `_call` answers 500 *"Unexpected error:
  …"* without logging. 🔴
- **The five `design-versions` routes:** every one raises `NotFoundError` from a
  stub → a plausible but misleading 404. 🔴

## Dependencies

- **`aeroplane-core`** — creates the lineage on `create_aeroplane` (BR-35), and
  its `GET /aeroplanes?heads_only=true` uses `list_aeroplanes_heads_only`.
- **Every owning module** — the clone copies their tables; a new table with an
  FK to `aeroplanes` must be registered in `CLONED_TABLES` or
  `EXCLUDED_TABLES` or the coverage test fails.
- **`ai-copilot`** — `copilot_apply_service` calls `create_branch` /
  `discard_branch` and is the only writer of `created_by = "copilot"`;
  `copilot_tools` imports the private `_metrics_payload`.
- **`wing-design`** — `spar_insert_service` calls `snapshot()` before a
  destructive commit and aborts if it fails (gh-1058).
- **`app/db/session.py` (`get_db`)** — owns the transaction (ADR 0009). Neither
  the service nor the clone ever commits.
- **Alembic `15f45e64a7c0`** — creates `branches`, adds the nine columns in
  batch mode, backfills a `main` branch per existing aeroplane with
  `INSERT … RETURNING id`, creates the partial index, and **drops**
  `design_versions`. The downgrade recreates `design_versions` **empty**.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| A version is a real aircraft row, not a serialised blob | ADR 0006; the whole clone engine | 🟢 |
| One-main-per-lineage is a **schema** constraint, not a code convention | `uq_branches_one_main_per_root` | 🟢 |
| The circular FK pair is accepted and resolved with `use_alter` + flush dances | model `:629-706`, `create_branch:207-232` | 🟢 |
| A snapshot preserves the head's identity by inserting itself behind it | `snapshot:150-183`; BR-38 | 🟢 |
| `restore` is `create_branch` plus an immutability requirement | `restore:291-321` | 🟢 |
| Deletion order is derived from SQLite's lack of deferrable FKs | `discard_branch:361-387` | 🟢 |
| The clone registry is a **test-enforced** invariant with mandatory reasons | `test_aeroplane_clone_coverage.py` | 🟢 |
| Unmappable component-tree parents are logged with both ids, never dropped silently | `_clone_component_tree:565-580` | 🟢 |
| Internal references are re-keyed; library references are shared | `_remap_component_overrides`; BR-40 | 🟢 |
| 🟢 Versioning routes expose UUIDs (`Q-VS-8`, ADR 0019) | `versioning.py` paths | 🟢 (a 🔴 inconsistency) |
| `compare` returns two payloads and leaves diffing to the client | `compare:396-412` | 🟢 |
| 🟢 `created_by` is fixed to the canonical `human` | `ai` vocabulary with a DB CHECK (`Q-CC-9`, maintainer-answered); agent detail moves to a separate field. | BR-VR15 | 🟢 (a 🔴 divergence) |

## Internal State

| State | Where | Lifecycle |
|---|---|---|
| The version DAG | `aeroplanes` (4 columns) | grown by snapshot / branch / restore; pruned only by `discard_branch` |
| Branch pointers | `branches` | created by `create_branch`; `head_id` never moves after creation 🟡; deleted by `discard_branch` |
| The main flag | `branches.is_main` | moved by `adopt_branch`, demote-first; guaranteed unique per lineage by the partial index |
| Version metadata | 5 columns on `aeroplanes` | set once by `snapshot`; cleared to `None` on every clone |
| `preview_png` | `aeroplanes` | **never written** 🟡 (`Q-VS-2`) |

A branch's `head_id` is set at creation and, in the code read here, never
updated — a new snapshot inserts itself *behind* the head rather than advancing
it, so the head pointer stays valid for the branch's lifetime. 🟡

## Observability

- `logger.info` on every mutating operation: `snapshot` (node → snapshot id +
  label), `create_branch` (source → branch, head, name), `adopt_branch`
  (promoted + demoted ids), `discard_branch` (branch + node count),
  `rename_branch` (id, new name, root). 🟢 This is the best-instrumented module
  in the cluster.
- `logger.warning` in `_clone_component_tree` naming both the old and new node
  ids when a parent cannot be mapped. 🟢
- The router's `_call` catch-all does **not** log. 🔴
- Nothing records storage growth: no count of nodes per lineage, no size
  accounting, no age of the oldest snapshot — despite every snapshot being a
  full subgraph copy. 🔴

## Risks and Gaps

- 🔴 **No storage-growth control.** Every snapshot copies the entire design
  subgraph, `spar_insert_service` snapshots automatically on every destructive
  commit, and there is no retention policy, prune or size accounting.
- 🔴 **`discard_branch` deletes by `branch_id` alone.** A snapshot created on
  branch A and conceptually adopted elsewhere is still deleted with A; inbound
  `predecessor_id` links are nulled, silently truncating survivors' lineage.
- 🔴 **`list_tree` cannot find orphaned nodes.** A node with a `NULL` `root_id`
  is invisible in the version graph even though it exists.
- 🔴 **`create_branch` performs no name-collision check** while `rename_branch`
  does — two branches in one lineage can share a name.
- 🔴 **`created_by` has four writers and three vocabularies** with no enum; a UI
  filtering on `'ai'` misses every copilot branch.
- 🔴 **`provenance_message_id` is write-only** — nothing resolves a snapshot back
  to the conversation turn that produced it.
- 🟡 **`preview_png`** — the column, the clone reset and the `VersionNode` field all exist; no code path generates a thumbnail (`Q-VS-2`). is never written.**
- 🟢 **`_get_node_by_uuid` becomes live** — it is the target of the UUID migration (`Q-VS-8`), not dead code. Previously code**; the whole versioning API is
  integer-PK, inconsistent with the rest of v2.
- 🔴 **`compare` does not diff** — the client must do it.
- 🟡 **`_metrics_payload` is promoted to a public function** (`Q-VS-7`, derived): a `_`-prefixed private function imported by three call sites across two modules promises an instability its callers do not honour. Previously reads `stability_results[-1]`**, the last row by
  insertion order rather than the newest by `computed_at`.
- 🔴 **The `design-versions` REST surface is dead but mounted**, returning a
  plausible 404 from a stub instead of a 410/501.
- 🔴 **The clone coverage test has a documented blind spot** for string-FK
  tables; three are maintained by hand today.
- 🟡 **`compare` does not require a shared lineage**, so two unrelated aircraft
  can be compared as if they were versions of one another.
- 🟡 **A branch's `head_id` never advances**, which is coherent with BR-38 but
  means the column is effectively write-once.
</content>
