# branch-model — Technical Design

> Use-case design, nested under the module [`versioning`](../design.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Full endpoint contract: [`../contracts.md`](../contracts.md).

## Interface

### `branches` 🟢

| Column | Type | Req. | Default |
|---|---|---|---|
| `id` | Integer PK | — | auto |
| `root_id` | Integer FK → `aeroplanes.id` (`use_alter`, `fk_branches_root_id`) | yes | — |
| `head_id` | Integer FK → `aeroplanes.id` (`use_alter`, `fk_branches_head_id`) | yes | — |
| `name` | String | yes | — |
| `is_main` | Boolean | yes | `False` (`server_default="false"`) |
| `created_by` | String | no | `NULL` |
| `created_at` | DateTime(tz) | yes | `func.now()` |

```sql
CREATE UNIQUE INDEX uq_branches_one_main_per_root
  ON branches (root_id) WHERE is_main = 1;    -- postgresql_where: is_main = true
```

Relationships: `BranchModel.root` ↔ `AeroplaneModel.root_branches`,
`BranchModel.head` ↔ `AeroplaneModel.head_branches`, both with explicit
`foreign_keys=` because two FKs point at the same table. 🟢

### Service 🟢

| Symbol | Line | Raises |
|---|---|---|
| `create_branch(db, from_node_id, name, created_by="human")` | 186 | `NotFoundError` |
| `adopt_branch(db, branch_id)` | 244 | `NotFoundError`, `ConflictError` |
| `discard_branch(db, branch_id)` | 324 | `NotFoundError`, `ConflictError` |
| `rename_branch(db, branch_id, name)` | 459 | `NotFoundError`, `ValidationError`, `ConflictError` |
| `list_tree(db, root_id)` | 415 | `NotFoundError` |
| `list_aeroplanes_heads_only(db)` | 515 | — |

### REST 🟢

| Method | Path | Status |
|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/branch` | **201** · 404 · 422 |
| POST | `/branches/{branch_id}/adopt` | 200 · 404 · **409** |
| PATCH | `/branches/{branch_id}` | 200 · 404 · **409** · 422 |
| DELETE | `/branches/{branch_id}` | **204** · 404 · **409** |
| GET | `/lineages/{root_id}/tree` | 200 · 404 |

All UUID-addressed (`Q-VS-8`). 🟢

## Main Flow

### F1 — Create (l.186-241) 🟢

```
source  = _get_node(db, from_node_id)          # head OR snapshot — no guard
root_id = source.root_id if source.root_id is not None else source.id

new_head = clone_aeroplane_subgraph(db, source,
                                    immutable=False,
                                    branch_id=None,            # ← not known yet
                                    predecessor_id=source.id,
                                    root_id=root_id)
new_head.created_by = created_by
db.flush()                                     # ① obtain new_head.id

branch = BranchModel(root_id=root_id, head_id=new_head.id,
                     name=name, is_main=False, created_by=created_by)
db.add(branch)
db.flush()                                     # ② obtain branch.id

new_head.branch_id = branch.id
db.flush()                                     # ③ close the cycle

logger.info("create_branch: source %s → new branch %s (head=%s, name=%r)", …)
```

The three flushes exist because `aeroplanes.branch_id` and `branches.head_id`
point at each other: neither row can be written complete in one statement. The
same dance appears in `aeroplane_service.create_aeroplane` (BR-35). 🟢

No name-collision query ran here — 🟢 one now does (`R2-04`); uniqueness is per `root_id`, enforced by a partial unique index.

### F2 — Adopt (l.244-288) 🟢

```
branch = _get_branch(db, branch_id)
if branch.is_main: raise ConflictError("Branch is already the main branch")

current_main = branches WHERE root_id = branch.root_id AND is_main == True
if current_main is not None:
    current_main.is_main = False
    db.flush()      # ← DEMOTE FIRST so the partial index never sees two mains

branch.is_main = True
db.flush()
```

Swap the two statements and the partial unique index rejects the write. The
`current_main is None` branch is reachable for a legacy lineage that was never
backfilled, and promotes anyway. 🟡

### F3 — Rename (l.459-512) 🟢

```
branch   = _get_branch(db, branch_id)
stripped = name.strip()
if not stripped: raise ValidationError("Branch name must not be empty")

conflict = branches WHERE root_id = branch.root_id
                      AND name    = stripped
                      AND id     != branch_id          # ← excludes itself
if conflict: raise ConflictError(details={branch_id, conflicting_branch_id, name})

branch.name = stripped ; db.flush()
```

The `id != branch_id` clause is what lets a no-op rename succeed. 🟢

### F4 — Discard (l.324-393) 🟢

```
branch = _get_branch(db, branch_id)

# ── guards ─────────────────────────────────────────────────────────────
branch.is_main                                   -> ConflictError (409)
COUNT(branches WHERE root_id = branch.root_id) <= 1
                                                 -> ConflictError (409)

# ── collect ────────────────────────────────────────────────────────────
nodes    = aeroplanes WHERE branch_id = branch_id
node_ids = {n.id for n in nodes}

# ── 3. null inbound predecessor links ──────────────────────────────────
UPDATE aeroplanes SET predecessor_id = NULL
WHERE predecessor_id IN node_ids                 synchronize_session="fetch"
# the FK is use_alter/deferred, but SQLite has no deferrable FKs

# ── 4. delete the BRANCH first ─────────────────────────────────────────
db.delete(branch) ; db.flush()
# otherwise SQLAlchemy nulls branches.head_id via the relationship and
# violates its NOT NULL constraint

# ── 5. delete the nodes ────────────────────────────────────────────────
for node in nodes: db.delete(node)               # ORM cascade → subgraph
db.flush()

logger.info("discard_branch: branch %s deleted, %s node(s) removed", …)
```

All five steps are commented in the source; none is incidental. 🟢

### F5 — Read paths 🟢

```
list_tree(root_id):
    _get_node(db, root_id)                       # 404 if unknown
    nodes    = aeroplanes WHERE id = root_id OR root_id = root_id  ORDER BY id
    branches = branches   WHERE root_id = root_id                  ORDER BY id
    → endpoint: is_head = n.id in {b.head_id for b in branches}

list_aeroplanes_heads_only():
    head_ids = SELECT head_id FROM branches                        # scalar subquery
    aeroplanes WHERE branch_id IS NULL OR id IN head_ids           ORDER BY name
```

`list_tree`'s filter cannot reach a node whose `root_id` is `NULL` — a legacy
row, or a clone created with `root_id=None`. 🔴

## Alternative Flows

- **Fork from a snapshot:** allowed; there is no immutability guard on
  `create_branch`. 🟢
- **Fork from a node whose `root_id` is `NULL`:** `root_id = source.id`, which
  silently starts a **new lineage** rooted at that node. 🟡
- **Adopt with no current main:** the demote is skipped; the branch is
  promoted. 🟡
- **Rename to the same name:** succeeds (the conflict query excludes itself). 🟢
- **Rename with surrounding whitespace:** stripped before both checks. 🟢
- **Discard the main branch / the only branch:** 409 each. 🟢
- **Discard a branch whose nodes are other nodes' predecessors:** those links
  are nulled — the survivors keep existing with a truncated lineage. 🔴
- **Discard when a node was already deleted:** the collect step simply returns
  fewer rows; no error. 🟡
- **`list_tree` on an unknown root:** 404 from `_get_node`. 🟢
- **`list_tree` on a lineage with orphaned nodes:** they are omitted with no
  indication. 🔴
- **Two branches sharing a name:** reachable through `create_branch`; only
  `rename_branch` complains. 🔴

## Dependencies

- **[`aeroplane-clone-subgraph`](../aeroplane-clone-subgraph/design.md)** —
  `create_branch` is a clone plus two rows; the clone is where the real work
  happens.
- **[`snapshot-immutability`](../snapshot-immutability/design.md)** — `restore`
  is `create_branch` with an immutability requirement, and snapshots are the
  nodes `discard_branch` most often removes.
- **[`copilot-provenance`](../copilot-provenance/design.md)** — the copilot's
  proposal branch is created and discarded through these two operations.
- **`aeroplane-core`** — bootstraps the first branch on `create_aeroplane`
  (BR-35) and consumes `list_aeroplanes_heads_only` for
  `GET /aeroplanes?heads_only=true`.
- **`app/db/session.py` (`get_db`)** — the transaction (ADR 0009).
- **Alembic `15f45e64a7c0`** — creates the table, backfills one main branch per
  existing aeroplane, and creates the partial index **after** the backfill.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| One-main-per-lineage is enforced by a partial unique index, not by application code | model + migration | 🟢 |
| The index is declared for both SQLite and PostgreSQL so tests and production agree | `sqlite_where` / `postgresql_where` | 🟢 |
| The circular FK pair is accepted and satisfied by an explicit three-flush sequence | `create_branch:207-232` | 🟢 |
| A branch may be forked from a snapshot, which makes `restore` a thin wrapper | no guard in `create_branch` | 🟢 |
| Adoption demotes first and flushes, because the index cannot see two mains | `:277` and its comment | 🟢 |
| The demoted branch is kept rather than deleted | `adopt_branch` | 🟢 |
| Discard order is derived from SQLite's non-deferrable FKs and the `head_id` NOT NULL constraint | `discard_branch:361-387` | 🟢 |
| 🟡 Re-point predecessors instead of truncating (`Q-VS-6`) | step 3 | 🟢 (a 🔴 consequence) |
| `is_head` is computed at the endpoint rather than stored | `versioning.py:277-296` | 🟢 |
| Legacy `branch_id IS NULL` rows stay visible in the picker | `list_aeroplanes_heads_only` | 🟢 |
| 🟢 Branch names are unique per `root_id`; `create_branch` enforces it too, backed by a partial unique index (`R2-04`) | `rename_branch` vs `create_branch` | 🟢 ( 🔴 asymmetry) |
| Every mutating operation logs its ids | four `logger.info` calls | 🟢 |

## Internal State

| State | Transition | Trigger |
|---|---|---|
| branch exists | — → feature branch | `create_branch` |
| `is_main` | feature → main (and the old main → feature) | `adopt_branch`, demote-first |
| `name` | renamed | `rename_branch` |
| branch + its exclusive nodes | → deleted | `discard_branch` |
| `head_id` | set once at creation, **never advanced** | — 🟡 |

The `head_id` column is effectively write-once: a snapshot inserts itself behind
the head (BR-38), so the pointer stays valid for the branch's whole life. 🟡

## Observability

- `logger.info` on all four mutating operations, each naming the ids involved
  (`create_branch` also names the head and the name; `adopt_branch` names the
  demoted branch; `discard_branch` names the node count). 🟢
- The router's `_call` catch-all raises 500 **without** logging. 🔴
- Nothing counts branches per lineage or nodes per branch, so unbounded growth
  is invisible until someone reads the tree. 🔴

## Risks and Gaps

- 🔴 **`create_branch` does not check for a name collision** while
  `rename_branch` does, so two branches in one lineage can share a name and only
  a later rename will complain.
- 🔴 **`discard_branch` deletes by `branch_id` alone** and nulls inbound
  `predecessor_id`s, silently truncating the lineage of surviving nodes.
- 🔴 **`list_tree` cannot see nodes with a `NULL` `root_id`.**
- 🔴 **Forking from a `NULL`-`root_id` node silently starts a new lineage**
  rooted at that node, which is unlikely to be what the caller meant.
- 🔴 **The routes are integer-PK addressed** while the rest of v2 uses UUIDs;
  `_get_node_by_uuid` exists and is dead.
- 🔴 **The router does not log its 500s.**
- 🟡 **`head_id` never advances**, so the column cannot express "this branch has
  moved on" — coherent today, surprising to a future contributor.
- 🟡 **Adoption on a mainless lineage succeeds silently**, which hides a
  backfill failure rather than surfacing it.
- 🟡 **Neither read path paginates**, so a long-lived lineage returns every node
  in one response.
</content>
