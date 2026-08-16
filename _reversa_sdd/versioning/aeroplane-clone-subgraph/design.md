# aeroplane-clone-subgraph — Technical Design

> Use-case design, nested under the module [`versioning`](../design.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> This use case has **no REST route**; it is called by
> [`snapshot-immutability`](../snapshot-immutability/design.md) and
> [`branch-model`](../branch-model/design.md).

## Interface

```python
clone_aeroplane_subgraph(
    db: Session,
    source: AeroplaneModel,
    *,
    immutable: bool,          # is_immutable on the new node
    branch_id: int | None,    # may be None — create_branch fills it in after
    predecessor_id: int | None,
    root_id: int | None,      # None means the caller sets it to the new id
) -> AeroplaneModel           # unflushed-metadata clone, children already added
```

Helpers: `_remap_component_overrides(overrides, weight_id_map) -> Any` (l.463)
and `_clone_component_tree(db, source, clone) -> None` (l.494).

Registry: `CLONED_TABLES: frozenset[str]` (17) and
`EXCLUDED_TABLES: dict[str, str]` (18, table → reason).

## Main Flow

### F1 — Group 1: the root row (l.184-206) 🟢

```python
clone = AeroplaneModel(
    uuid=uuid4(),                                     # NEW identity
    name=source.name,
    total_mass_kg=source.total_mass_kg,
    flight_profile_id=source.flight_profile_id,       # SHARED ref — kept
    xyz_ref=copy.deepcopy(source.xyz_ref),
    assumption_computation_context=copy.deepcopy(
        source.assumption_computation_context),
    is_immutable=immutable,
    branch_id=branch_id,
    predecessor_id=predecessor_id,
    root_id=root_id,
    version_label=None, version_note=None, created_by=None,   # caller's job
    …)
```

`copy.deepcopy` on both JSON columns is what stops two versions from sharing a
mutable structure — an aliasing bug that would be invisible until one of them
was edited. 🟢

### F2 — Group 2: weight items + the map (l.207-225) 🟢

```
weight_id_map: dict[str, str] = {}
for wi in source.weight_items:
    new_wi = WeightItemModel(aeroplane_id=clone.id, …)
    db.add(new_wi) ; db.flush()
    weight_id_map[str(wi.id)] = str(new_wi.id)      # STRING keys
```

The keys are strings because `loading_scenarios.component_overrides` stores
`str(weight_item.id)` in its `component_uuid` fields. 🟢

### F3 — Group 3: the wing hierarchy (l.226-338) 🟢

Five levels, each flushed so the next can reference it:

```
wings
 └ wing_xsecs
    └ wing_xsec_details
       ├ wing_xsec_spares
       ├ wing_xsec_turbulators            (1:1, gh-1069)
       └ wing_xsec_trailing_edge_devices
          └ wing_xsec_ted_servos          component_id KEPT (shared COTS ref)
```

The servo's `component_id` is the one FK in this subtree that must **not** be
re-keyed: it points into the global component library, not into the aircraft. 🟢

### F4 — Group 4: fuselages (l.339-361) 🟢

```
fuselages  →  fuselage_xsecs
step_path = None ; solid_step_path = None
```

Nulling the artefact paths is deliberate: a clone that inherited them would
serve the *source's* STEP file as its own geometry. 🟢

### F5 — Groups 5-8 (l.362-438) 🟢

| Group | Table | Note |
|---|---|---|
| 5 | `mission_objectives` | 1:1 per aeroplane |
| 6 | `design_assumptions` | estimate + calculated + `active_source` + divergence — the full triple (ADR 0010) |
| 7 | `aircraft_computation_config` | 1:1 |
| 8 | `stability_results` | **including `computed_at` and `geometry_hash`** 🟡 |

Group 8's decision means a clone inherits a result that appears to have been
computed at the original time against the original geometry hash — correct for
an immutable snapshot (the geometry really is that one), arguably misleading for
a mutable branch head that will now diverge. 🟡

### F6 — Group 9: loading scenarios (l.439-450) 🟢

```
for ls in source.loading_scenarios:
    new_overrides = _remap_component_overrides(ls.component_overrides, weight_id_map)
    db.add(LoadingScenarioModel(aeroplane_id=clone.id, …,
                                component_overrides=new_overrides, …))
```

### F7 — `_remap_component_overrides` (l.463-491) 🟢

```
if not overrides or not weight_id_map:
    return deepcopy(overrides) if overrides else overrides

result = deepcopy(overrides)
for list_key in ("toggles", "mass_overrides", "position_overrides"):
    for item in result.get(list_key) or []:
        if isinstance(item, dict) and "component_uuid" in item:
            item["component_uuid"] = weight_id_map.get(item["component_uuid"],
                                                       item["component_uuid"])
return result
```

The `.get(old, old)` fallback is the load-bearing line: a value **not** in the
map is a COTS component UUID — a shared reference — and must pass through
untouched. Without the remap, a clone's loading scenarios would silently
describe the **source's** weight items. 🟢

### F8 — Group 10: `_clone_component_tree` (l.494-580) 🟢

```
old_uuid_str = str(source.uuid)
nodes = component_tree WHERE aeroplane_id = old_uuid_str  ORDER BY id
if not nodes: return

new_uuid_str = str(clone.uuid)
id_map: dict[int, int] = {}

# ── pass 1: insert every node with parent_id = None ──────────────────────
for node in nodes:
    new_node = ComponentTreeNodeModel(
        aeroplane_id=new_uuid_str,
        parent_id=None,                       # fixed in pass 2
        sort_index, node_type, name, shape_key, shape_hash,
        volume_mm3, area_mm2,
        component_id,                          # SHARED COTS ref — kept
        quantity, construction_part_id,        # SHARED ref — kept
        pos_x/y/z, rot_x/y/z,
        material_id,                           # SHARED ref — kept
        weight_override_g, print_type, scale_factor, synced_from)
    db.add(new_node) ; db.flush()              # ← per-node flush 🔴
    id_map[node.id] = new_node.id

# ── pass 2: restore the parent links ─────────────────────────────────────
for node in nodes:
    if node.parent_id is None: continue
    new_parent_id = id_map.get(node.parent_id)
    if new_parent_id is not None:
        UPDATE component_tree SET parent_id = new_parent_id
        WHERE id = id_map[node.id]             # 🟢 accepted (R2-08): largest tree measured = 10 nodes, mean 4.5
    else:
        logger.warning("… node %s (source id=%s) has parent_id=%s that is not "
                       "in the cloned node set for aeroplane %s → %s. "
                       "parent_id left as None on the cloned node.", …)
```

Two passes are necessary because a child may be inserted before its parent, and
the table is found by a **string** `aeroplane_id` rather than an integer FK
(which is why the coverage test cannot see it). The warning names **both** ids —
an explicit choice over silent data loss. 🟢

## Alternative Flows

- **Source with no weight items:** `weight_id_map` is empty;
  `_remap_component_overrides` short-circuits and deep-copies the overrides
  unchanged. 🟢
- **Source with no component tree:** `_clone_component_tree` returns
  immediately. 🟢
- **`component_overrides` is `None` or `{}`:** returned as-is / deep-copied
  without touching any list. 🟢
- **An override list contains a non-dict entry:** skipped by the
  `isinstance(item, dict)` guard. 🟢
- **A tree node whose parent belongs to another aeroplane** (cross-aeroplane
  reference or corrupt data): `parent_id` stays `None` and the warning fires;
  the node becomes a root of the cloned tree. 🟢
- **A tree node with a `NULL` `parent_id`:** skipped in pass 2 — it is already
  a root. 🟢
- **`root_id=None` passed by the caller:** the clone's `root_id` is `NULL` and
  the caller must set it to the new id. 🟡 Nothing enforces that it does — a
  caller that forgets creates a node invisible to `list_tree`. 🔴
- **`branch_id=None`:** legitimate — `create_branch` back-fills it after the
  branch row exists. 🟢
- **A column added to a cloned model but not to the clone's constructor call:**
  silently dropped from every future version. 🔴 No test compares the copied
  field set against the model.
- **A new table with an FK to `aeroplanes`:** the coverage test fails until it
  is registered. 🟢
- **A new table with a *string* aeroplane reference:** the coverage test
  **passes** and the table is silently not cloned. 🔴

## Dependencies

- **Every owning module** — the clone touches wings, fuselages, weight items,
  the mission objective, assumptions, the computation config, stability results,
  loading scenarios and the component tree. Any schema change in those modules
  is a change here.
- **[`snapshot-immutability`](../snapshot-immutability/design.md)** and
  **[`branch-model`](../branch-model/design.md)** — the only callers.
- **`app/db/session.py` (`get_db`)** — the transaction (ADR 0009); the clone
  flushes but never commits.
- **`test_aeroplane_clone_coverage.py`** — the enforcement mechanism; without it
  the registry is documentation.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| A version is a full row copy rather than a delta or a serialised blob | ADR 0006 | 🟢 |
| Completeness is enforced by a test that introspects the schema, not by review | `test_aeroplane_clone_coverage.py` | 🟢 |
| Every exclusion must carry a written reason | `EXCLUDED_TABLES` is a dict, not a set | 🟢 |
| The registry's blind spot is documented at the point of use rather than fixed | the comment above `CLONED_TABLES` | 🟢 (a 🔴 gap) |
| Library references are kept; aircraft-internal references are re-keyed | BR-40 | 🟢 |
| An unmapped override value is assumed to be a COTS uuid and passed through | `_remap_component_overrides:489` | 🟢 |
| The component tree is cloned in two passes because a child may precede its parent | `_clone_component_tree` | 🟢 |
| An unmappable parent is logged with both ids rather than silently dropped | `:565-580` | 🟢 |
| JSON columns are deep-copied so versions cannot alias | `copy.deepcopy` | 🟢 |
| Artefact paths are nulled so a version never serves another's files | group 4 | 🟢 |
| Stability results keep their original `computed_at` and `geometry_hash` | group 8 | 🟢 (a 🟡 ambiguity) |
| Version metadata is the caller's responsibility, not the clone's | `:198-200` | 🟢 |

## Internal State

The clone holds two maps for the duration of one call:

| Map | Built in | Consumed by | Key type |
|---|---|---|---|
| `weight_id_map` | group 2 | group 9 (`_remap_component_overrides`) | `str → str` |
| `id_map` | `_clone_component_tree` pass 1 | pass 2 | `int → int` |

Neither is persisted. Everything else is written straight through to the
session. 🟢

## Observability

- `logger.warning` naming both the source and cloned node ids when a
  component-tree parent cannot be mapped — the module's most valuable log line,
  because it is the only signal that a clone is structurally incomplete. 🟢
- **No log line on the success path.** A clone of a 500-node aircraft is
  invisible in the logs; the caller (`snapshot` / `create_branch`) logs
  instead. 🟡
- Nothing counts rows copied, time taken or storage consumed. Given that every
  snapshot is a full subgraph copy and `spar_insert_service` takes them
  automatically, this is the module's largest observability gap. 🔴

## Risks and Gaps

- 🔴 **The coverage test's blind spot is open.** Any future table whose
  aeroplane reference is a plain `String` is invisible to the BFS and will
  silently not be cloned. Three such tables exist today and are maintained by
  hand.
- 🔴 **Nothing verifies the copied *field* set.** The registry checks which
  *tables* are cloned, not which *columns*. A column added to a cloned model but
  omitted from the constructor call is silently lost on every subsequent
  version — the same class of bug the registry was built to prevent, one level
  down.
- 🔴 **`root_id=None` is accepted with no follow-up check.** A caller that
  forgets to set it produces a node invisible to `list_tree`.
- 🔴 **Pass 1 flushes per node** and pass 2 issues one `UPDATE` per node, so a
  large component tree costs O(n) round-trips twice. On a 500-node tree that is
  1000 statements per snapshot.
- 🔴 **No storage accounting.** Every snapshot duplicates the entire design
  subgraph; nothing measures or bounds the growth.
- 🔴 **No success-path logging**, so a partially failing clone is only visible
  through the one warning.
- 🟡 **Cloned stability results carry the original `computed_at` and
  `geometry_hash`**, which is right for an immutable snapshot and misleading for
  a mutable branch head.
- 🟡 **`_remap_component_overrides` assumes the three list keys.** A future
  override category would be copied unmapped and would silently reference the
  source's weight items.
- 🟡 **The clone is unbounded.** There is no depth limit, node cap or timeout;
  a pathologically large aircraft would block its request for the whole copy.
</content>
