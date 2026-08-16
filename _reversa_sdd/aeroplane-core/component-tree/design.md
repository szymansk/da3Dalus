# component-tree — Technical Design

> Use-case design, nested under the module [`aeroplane-core`](../design.md).
> Focuses on HOW the use case is built, derived from the legacy code.
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Full module-level endpoint contract: [`../contracts.md`](../contracts.md).

## Interface

### Service surface — `app/services/component_tree_service.py` 🟢

| Symbol | Purpose | Line |
|---|---|---|
| `get_tree` | read the whole tree for an aeroplane UUID, assembled and ordered | l.123 |
| `_build_tree` | id-map + parent attach, orphan-tolerant, `sort_index` ordering | l.58-79 |
| `_snapshot_construction_part_fields` | copy part metrics into a new node, `exclude_unset`-aware | l.162-187 |
| `move_node` | reparent a node after the cycle guard | l.324 |
| `_is_descendant` | ancestor-chain walk backing the cycle guard | l.339-359 |

`get_tree` also computes the weight fields, but that logic is specified in
[`../weight-rollup/design.md`](../weight-rollup/design.md) — this document covers
only the structural half.

### REST surface — `app/api/v2/endpoints/aeroplane/component_tree.py` (l.52-128) 🟢

Base path: `/aeroplanes/{aeroplane_id}/component-tree`, where `{aeroplane_id}` is
the public UUID.

| Method | Path suffix | Operation | Status codes |
|---|---|---|---|
| GET | `` | read the whole tree | 200 · 404 · 500 |
| POST | `` | add a node | **201** · 404 · 422 · 500 |
| PUT | `/{node_id}` | partial update | 200 · 404 · 422 · 500 |
| DELETE | `/{node_id}` | delete a node and its subtree | 200 · 404 · 500 |
| POST | `/move` | reparent a node | 200 · **422 on a descendant target** · 404 · 500 |

`GET /weight` is deliberately out of scope — see
[`../weight-rollup/design.md`](../weight-rollup/design.md).

### Data model — `component_tree` (`ComponentTreeNodeModel`) 🟢

| Field | Type | Meaning |
|---|---|---|
| `id` | Integer PK | node identity, used in the route path |
| `aeroplane_id` | **String, indexed** | the aeroplane UUID — **not** a foreign key |
| `parent_id` | int \| null | null ⇒ root |
| `sort_index` | int | sibling ordering |
| `node_type` | `"group"` \| `"cad_shape"` \| `"cots"` | free-text discriminator |
| `weight_override_g` | float \| null | grams — consumed by `weight-rollup` |
| `component_id` | int \| null | COTS component reference |
| `quantity` | int | multiplier for COTS mass |
| `construction_part_id` | int \| null | snapshot source for the three metric fields |
| `volume_mm3`, `area_mm2` | float \| null | CAD-shape metrics, mm³ / mm² |
| `material_id` | int \| null | material component supplying `density_kg_m3` |
| `print_type` | `"volume"` \| `"surface"` | selects the weight formula |
| `print_resolution_mm` | float | default **0.4**, surface prints only |
| `scale_factor` | float | multiplier on the calculated mass |
| `synced_from` | string \| null | `"wing:<name>"` / `"fuselage:<name>"` for auto-synced groups |

Structural fields owned here are `id`, `aeroplane_id`, `parent_id`,
`sort_index`, `node_type`, `construction_part_id` and `synced_from`; the
remaining columns are stored here but interpreted by `weight-rollup`.

## Main Flow

### F1 — Read the tree (`get_tree`, l.123-160) 🟢

1. Load **all** nodes for the aeroplane UUID in one indexed query.
2. Pre-compute the per-node own weights into a dict (l.133-137) — see
   [`../weight-rollup/design.md`](../weight-rollup/design.md).
3. `_build_tree` assembles the hierarchy (F2).
4. `_roll_up_weights` decorates the tree with the computed weight fields
   (`weight-rollup`).
5. Return the roots.

### F2 — Assemble the hierarchy (`_build_tree`, l.58-79) 🟢

```
pass 1:  node_map = { node.id: node for node in rows }
pass 2:  for node in rows:
             parent = node_map.get(node.parent_id)
             if parent is not None:  parent.children.append(node)
             else:                   roots.append(node)      # includes orphans
sort:    children and roots ordered by sort_index
```

The `else` branch is load-bearing: a node whose `parent_id` refers to a row that
is absent from the map (deleted out-of-band, or belonging to another aeroplane)
is **promoted to a root** rather than dropped or raising. 🟢

### F3 — Create a node (POST ``) 🟢

1. Resolve the aeroplane UUID (404 if absent).
2. If `construction_part_id` is set, run `_snapshot_construction_part_fields`
   (F5) before persisting.
3. `db.add()` the node with its `node_type`, `parent_id` and `sort_index`.
4. Trigger `_sync_aircraft_mass` (fire-and-forget — see `weight-rollup`).
5. Answer **201** with the node id.

### F4 — Update and delete 🟢

- **Update (`PUT /{node_id}`)** applies a *partial* patch: fields absent from the
  payload are left untouched, matching the `exclude_unset` semantics used
  throughout the service. Answers **200**.
- **Delete (`DELETE /{node_id}`)** removes the node **only if it has no
  children**; a node with children is rejected with **409**, naming the blocking
  child count (`Q-AC-10`). 🟢 The relationship cascade remains in the DDL as a
  safety net against direct SQL, but the service never relies on it and no
  acceptance criterion may describe subtree deletion as a feature. The frontend
  shows the blocking count and offers to select the subtree so the user deletes
  leaf-first — deliberately **without** a "delete anyway" flag, which would
  reintroduce the silent destruction this decision removes.

Both paths end with the fire-and-forget mass sync.

### F5 — Construction-part snapshot (`_snapshot_construction_part_fields`, l.162-187) 🟢

```
supplied = data.model_dump(exclude_unset=True)
for field in ("volume_mm3", "area_mm2", "material_id"):
    if field not in supplied:
        setattr(node, field, getattr(construction_part, field))
```

Only fields the caller **did not mention** are filled. An explicitly supplied
value — including an explicit `None` — survives untouched. 🟢

### F6 — Move a node (`move_node`, l.324+) 🟢

1. Load the moved node and the target parent (404 if either is absent).
2. Walk the ancestor chain of the target with `_is_descendant` (l.339-359); if
   the moved node appears anywhere on that chain, raise `ValidationError`
   (→ **422**) and mutate nothing.
3. Reassign `parent_id` and `sort_index`.
4. `_sync_aircraft_mass` (fire-and-forget).

This is the **only** structural integrity check in the module. 🟢

### F7 — Group auto-sync hooks (gh#108) 🟢

`wing_service` and `fuselage_service` call into this use case:

```
create wing/fuselage  ->  create a group node with synced_from = "<kind>:<name>"
delete wing/fuselage  ->  delete nodes whose synced_from matches that prefix
```

(`wing_service.create_wing:298-300`, `fuselage_service.delete_fuselage:179-181`.)
Because those services also depend on this module, the dependency is
bidirectional and is broken by lazy imports inside the functions.

## Alternative Flows

- **Aeroplane or node not found:** `NotFoundError` → **404** with
  `{"error": {"code": "not_found", …}}` via `_raise_http_from_domain`.
- **Move into a descendant:** `ValidationError` → **422**, nothing written. 🟢
- **Orphan node on read:** silently promoted to a root by `_build_tree`, rather
  than dropped or erroring. 🟢
- **Mass sync failure on any write:** caught and logged inside
  `_sync_aircraft_mass`; the CRUD response is unaffected (see `weight-rollup`). 🟢
- **A fourth `node_type` value:** nothing rejects it at the database level; the
  weight resolution would simply fall through to `(None, "none")`. 🟡
- **Unexpected exception in any handler:** defensive `except Exception → 500`. 🟢

## Dependencies

- **`app/db/session.py` (`get_db`)** — owns the transaction; this use case never
  commits (ADR 0009).
- **[`weight-rollup`](../weight-rollup/design.md)** — decorates the assembled
  tree with `own_weight_g`, `total_weight_g` and `weight_status`, and is invoked
  from every write via `_sync_aircraft_mass`.
- **`construction-plans`** — supplies the construction part whose `volume_mm3` /
  `area_mm2` / `material_id` are snapshotted on create.
- **`powertrain` / COTS catalogue (`components`)** — supplies `component_id` for
  `cots` nodes and `material_id` for calculated weights.
- **`wing-design` / `fuselage-design`** — call *into* this use case for the group
  auto-sync, producing a two-way dependency resolved by lazy imports.
- **`app/core/exceptions.py`** — the `ServiceException` hierarchy.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| The tree is assembled in memory from one flat query, not walked recursively in SQL | `component_tree_service.py:123-160` | 🟢 |
| Orphans are promoted to roots rather than rejected — the read path never fails on inconsistent data | `_build_tree:58-79` | 🟡 |
| Cycles are prevented on **write** only; the read path assumes acyclicity | `move_node:324-325`, `_is_descendant:339-359` | 🟢 |
| `node_type` is a free-text column, not an enum | `component_tree.py:12-16` | 🟢 |
| `component_tree.aeroplane_id` is a denormalised UUID string, not an FK | `app/models/component_tree.py` | 🟢 (consequence 🔴) |
| Partial updates use `exclude_unset` so an omitted field is never cleared | `_snapshot_construction_part_fields:162-187` | 🟢 |
| Ordering is applied during assembly rather than in the query | `_build_tree:58-79` | 🟢 |
| The wing/fuselage ↔ tree dependency is bidirectional and broken by lazy imports | `wing_service.py:298-300`, `fuselage_service.py:179-181` | 🟢 |

## Internal State

The use case is stateless between requests. Persistent state:

- `component_tree` rows — the BoM hierarchy: identity, parentage, ordering, type
  and the `synced_from` provenance marker.

Nothing structural is computed and persisted: `children`, the root set and the
weight fields all exist only in the response.

## Observability

- `logger.exception` on 5xx; 4xx are logged at INFO by the global handler
  (`app/main.py` error handlers). 🟢
- The swallowed mass-sync failure is logged by `weight-rollup`'s
  `_sync_aircraft_mass`. 🟢
- No metrics, traces or structured event emission in this use case. 🟢

## Risks and Gaps

- 🟢 **Read-side depth limiting is added**, reported as a `DesignWarning`
  (`Q-AC-3`). The `move_node` write guard is not sufficient on its own.
- 🟢 **Tree nodes become FK-bound to the aeroplane** (`Q-CC-7`), which is what
  stops the orphaned rows that exist today.
- 🟢 **Subtree deletion is no longer a contract at all** (`Q-AC-10`): a node with
  children cannot be deleted. The cascade stays in the DDL but is unreachable
  through the service, so a change to the relationship configuration can no
  longer silently orphan children.
- 🟢 **`node_type` gains a DB CHECK constraint** (`Q-CC-9`), so a typo is
  rejected at write time instead of producing a node that renders, resolves no
  weight and silently degrades its parent to `partial`.
- 🟢 **Negative `scale_factor` and `quantity` are rejected at the schema**
  (`Q-AC-4`). They are not a deliberate "credit" affordance; nothing in the
  own-weight chain rejects them today and they would **subtract** from the
  aircraft total.
- 🟡 **`sort_index` is not unique among siblings.** Ties are resolved by whatever
  order the sort is stable over, so two siblings sharing an index have an
  implementation-defined relative order.
