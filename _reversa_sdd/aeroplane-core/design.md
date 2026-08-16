# aeroplane-core — Technical Design

> Module-level design. Focuses on HOW the module is built, derived from the
> legacy code. Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Endpoint contracts in full: see [`contracts.md`](contracts.md).

## Interface

### Service surface — `app/services/aeroplane_service.py` 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `list_all_aeroplanes` | `(db: Session)` | `List[AeroplaneModel]` | ordered by `name` (l.47) |
| `create_aeroplane` | `(db: Session, name: str)` | `AeroplaneModel` | creates the row **and** the versioning lineage (l.61) |
| `get_aeroplane_by_uuid` | `(db, aeroplane_uuid)` | `AeroplaneModel` | raises `NotFoundError` (l.106) |
| `get_aeroplane_schema` | `(db, aeroplane_uuid)` | `AeroplaneSchema` | full nested read model (l.129) |
| `delete_aeroplane` | `(db, aeroplane_uuid)` | `None` | ORM cascade + best-effort STEP cleanup (l.169) |
| `get_aeroplane_mass` | `(db, aeroplane_uuid)` | `float` | raises `NotFoundError` (l.201) |
| `set_aeroplane_mass` | `(db, aeroplane_uuid, total_mass_kg: float)` | `bool` | `True` when newly created (l.218) |
| `get_aeroplane_airplane_configuration` | `(db, aeroplane_uuid)` | `dict` | CAD-side `AirplaneConfiguration` (l.252) |
| `_to_json_compatible` | `(value)` | JSON-safe value | recursive NumPy stripper (l.33-44) |

### Service surface — `app/services/component_tree_service.py` 🟢

| Symbol | Purpose | Line |
|---|---|---|
| `get_tree` | read the whole tree with roll-up | l.123 |
| `_build_tree` | id-map + parent attach, orphan-tolerant | l.58-79 |
| `_roll_up_weights` | post-order total + status | l.82-120 |
| `_calculate_own_weight` | precedence chain → `(grams, source)` | l.461-474 |
| `_snapshot_construction_part_fields` | copy part metrics into a new node | l.162-187 |
| `move_node` / `_is_descendant` | reparent + cycle guard | l.324, l.339-359 |
| `get_aircraft_total_weight_kg` | sum over roots, grams → kg, `None` if empty | l.381-403 |
| `_sync_aircraft_mass` | fire-and-forget push into `mass_cg_service` | l.362-378 |

### Data model 🟢

`aeroplanes` (`AeroplaneModel`, `app/models/aeroplanemodel.py:662`) — key columns:
`uuid` (GUID, unique, the public identifier), `name`, `total_mass_kg` (nullable),
`xyz_ref` (JSON `[x,y,z]`, metres, default `[0,0,0]`),
`assumption_computation_context` (JSON, the gh-924 aero truth cache),
`flight_profile_id` FK, plus the versioning columns
`branch_id` / `predecessor_id` / `root_id` / `is_immutable` / `version_label` /
`version_note` / `created_by` / `provenance_message_id` / `preview_png`.

Cascading relations (`all, delete-orphan`): `wings`, `fuselages`, `weight_items`,
`copilot_messages`, `design_assumptions`, `computation_config` (1:1),
`stability_results`, `loading_scenarios`, `mission_objective` (1:1).
`flight_profile` is many-to-one **without** cascade.
🟢 (`app/models/aeroplanemodel.py:718-795`)

`component_tree` (`ComponentTreeNodeModel`) — `aeroplane_id` is a plain indexed
**String** holding the aeroplane UUID, `parent_id`, `sort_index`, `node_type`
(`group` | `cad_shape` | `cots`), `weight_override_g`, `quantity`,
`component_id` (COTS), `construction_part_id`, `volume_mm3`, `area_mm2`,
`material_id`, `print_type` (`volume` | `surface`), `print_resolution_mm`,
`scale_factor`, `synced_from`. 🟢

## Main Flow

### F1 — Create aeroplane (`create_aeroplane`, l.61-104) 🟢

1. Instantiate `AeroplaneModel(name=name)` and `db.add()`.
2. `db.flush()` — the id is now assigned but nothing is committed.
3. Set `aeroplane.root_id = aeroplane.id` (a lineage root points at itself).
4. Create `BranchModel(root_id=id, head_id=id, name="main", is_main=True,
   created_by="human")`, `db.add()`, `db.flush()`.
5. Back-fill `aeroplane.branch_id = branch.id`.
6. Return the model. The commit happens in `get_db()` when the request succeeds.

The `flush()` sequence is mandatory: the two FKs are mutually circular, declared
with `use_alter=True` so the DDL emits them as separate `ALTER TABLE`
constraints rather than an unsatisfiable inline pair.

### F2 — Read nested aircraft (`get_aeroplane_schema`, l.129-167) 🟢

1. Resolve the aeroplane by UUID (404 if absent).
2. **Materialise** — iterate `aeroplane.wings → wing.x_secs → xsec.detail →
   detail.spares`, `detail.trailing_edge_device.servo_data` and the fuselages,
   touching each attribute so SQLAlchemy issues the SELECTs while the session is
   still open (l.141-149).
3. Build `AeroplaneSchema.model_validate(aeroplane)` (`from_attributes=True`).
4. Return; FastAPI serialises **after** `get_db()` has closed the session, which
   is exactly why step 2 exists.

### F3 — AirplaneConfiguration export (`get_aeroplane_airplane_configuration`, l.252+) 🟢

1. Resolve the aeroplane.
2. If `total_mass_kg is None` → raise `ValidationError` (→ 422). No conversion is
   attempted (l.263-267).
3. Convert the wings and fuselages through
   `app/converters/model_schema_converters.py` into the `cad_designer`
   `AirplaneConfiguration` (mm world; `scale = 1000.0`).
4. Run `_to_json_compatible` over the result so no `np.ndarray` / `np.generic`
   survives.
5. Return the dict; the endpoint wraps it in `AirplaneConfigurationResponse`.

### F4 — Component-tree read (`get_tree`, l.123-160) 🟢

1. Load all nodes for the aeroplane UUID in one query.
2. Pre-compute every node's own weight into a dict (l.133-137) so the recursion
   issues no further queries.
3. `_build_tree`: pass 1 builds `id → node`; pass 2 attaches each node to its
   `parent_id`. **A node whose parent is not in the map becomes a root**
   (orphan-tolerant). Children and roots are sorted by `sort_index`.
4. `_roll_up_weights` post-order:

   ```
   total_weight_g(node) = (own_weight_g or 0) + Σ total_weight_g(children)

   weight_status:
     leaf      → "valid"   if own source ≠ "none" else "invalid"
     non-leaf  → all children valid   → "valid"
                 all children invalid → "partial" if own weight present else "invalid"
                 mixed                → "partial"
   ```

5. Return the roots.

### F5 — Own-weight resolution (`_calculate_own_weight`, l.461-474) 🟢

Strict precedence, first match wins:

1. `weight_override_g` present → `(weight_override_g, "override")`
2. COTS node → `(component.mass_g × quantity, "cots")` (l.432-439)
3. CAD shape with a material density → `"calculated"` (l.442-458):

   ```
   surface print:  area_mm2 × print_resolution_mm × density_kg_m3 / 1e6 × scale_factor
   volume print:   volume_mm3                    × density_kg_m3 / 1e6 × scale_factor

   print_resolution_mm defaults to 0.4
   ```

4. otherwise `(None, "none")`

### F6 — Move node (`move_node`, l.324+) 🟢

1. Load the moved node and the target parent.
2. Walk the ancestor chain of the target with `_is_descendant`; if the moved node
   appears, raise `ValidationError` (→ 422).
3. Reassign `parent_id` and `sort_index`.
4. `_sync_aircraft_mass` (fire-and-forget).

### F7 — Aircraft total weight (`get_aircraft_total_weight_kg`, l.381-403) 🟢

Sum own + recursive children weights over every `parent_id IS NULL` root, in
grams, then divide by 1000. **Returns `None` for an empty tree** so the caller
clears the mass `calculated_value` instead of writing a zero.

## Alternative Flows

- **Aeroplane not found (any route):** service raises `NotFoundError`; the
  endpoint's `_raise_http_from_domain` maps it to **404** with
  `{"error": {"code": "not_found", ...}}`.
- **Missing mass on export:** `ValidationError` → **422**, before conversion.
- **STEP cleanup failure on delete:** caught by a bare `except`, logged, delete
  still succeeds (orphaned artefacts are accepted).
- **Mass sync failure on a tree write:** caught in `_sync_aircraft_mass`, logged,
  the CRUD response is unaffected.
- **Orphan tree node (parent missing):** silently promoted to a root by
  `_build_tree`, rather than dropped or erroring. 🟢
- **Duplicate name:** there is no uniqueness constraint on `aeroplanes.name`;
  two aeroplanes may share a name and are distinguished by UUID. 🟡 INFERRED
  from the absence of a unique index.
- **Unexpected exception in any handler:** each handler carries a defensive
  `except Exception → 500` fallback in addition to the domain mapping.

## Dependencies

- **`app/db/session.py` (`get_db`)** — owns the transaction; the module never
  commits (ADR 0009).
- **`app/converters/model_schema_converters.py`** — the conversion hub for the
  `AirplaneConfiguration` assembly (wings/fuselages → `cad_designer` topology).
- **`versioning` (`BranchModel`)** — the lineage created at birth; all further
  branch/snapshot operations live in that module.
- **`mass-and-balance` (`mass_cg_service`)** — pulled in via a **lazy import
  inside the function** to break the `component_tree_service ↔ mass_cg_service`
  import cycle.
- **`openvsp_step_export_service`** — best-effort artefact cleanup on delete.
- **`wing-design` / `fuselage-design`** — call *into* this module for the
  component-tree group auto-sync (gh#108), producing a two-way dependency
  resolved by lazy imports.
- **`app/core/exceptions.py`** — the `ServiceException` hierarchy.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Public identity is a UUID, internal identity an integer PK | `AeroplaneModel.uuid` unique + all v2 routes take `aeroplane_id` as UUID | 🟢 |
| Versioning is by row copy, not JSON snapshots — hence every aeroplane is a node | ADR 0006; `create_aeroplane:75-100` | 🟢 |
| Exactly one main branch is a **database** invariant, not an application check | partial unique index `uq_branches_one_main_per_root`, `aeroplanemodel.py:616-624` | 🟢 |
| Lazy loads are forced manually rather than by `selectinload` eager options | `aeroplane_service.py:141-149` | 🟢 |
| Best-effort side effects never fail the primary operation | `aeroplane_service.py:191-198`, `component_tree_service.py:362-378` | 🟢 |
| An absent value is reported as `null`, never as a fabricated `0` | `get_aircraft_total_weight_kg:381-403`; ADR 0012 | 🟢 |
| `node_type`, `created_by`, `print_type` are free-text columns, not enums | `component_tree.py:12-16`, `aeroplanemodel.py:641, 710` | 🟢 |
| The component tree tolerates orphans instead of rejecting them | `_build_tree:58-79` | 🟡 |
| `component_tree.aeroplane_id` is a denormalised UUID string, not an FK | `app/models/component_tree.py` | 🟢 (consequence 🔴) |

## Internal State

The module is stateless between requests. Persistent state:

- `aeroplanes` row — identity, mass, `xyz_ref`, the cached
  `assumption_computation_context`, and the versioning pointers.
- `component_tree` rows — the BoM hierarchy; `total_weight_g` and
  `weight_status` are **computed at read time**, never persisted.
- `branches` row — created here, evolved by `versioning`.

The `heads_only` flag is the only read-time projection of versioning state into
this module.

## Observability

- `logger.exception` on 5xx and on the swallowed STEP-cleanup / mass-sync
  failures; 4xx are logged at INFO by the global handler
  (`app/main.py` error handlers). 🟢
- No metrics, traces or structured event emission in this module. 🟢
- The event bus (`GeometryChanged`, `AssumptionChanged`) is published by
  `wing-design` / `mission-and-sizing`, not by `aeroplane-core`. 🟢

## Risks and Gaps

- 🔴 **Read-time recursion is unguarded.** `_build_tree` and `_roll_up_weights`
  assume acyclicity; only `move_node` prevents creating a cycle. Direct SQL, an
  import path or a future bulk endpoint could produce one, causing unbounded
  recursion on every subsequent read.
- 🔴 **Tree nodes are not FK-bound to the aeroplane.** Deleting an aeroplane
  leaves its `component_tree` rows behind. Whether cleanup happens elsewhere is
  unknown.
- 🔴 **Dead legacy router.** `app/api/v2/endpoints/aeroplane.py` is shadowed by
  the package `aeroplane/`; it wires only 3 of 24 sub-routers and is never
  imported. Retained deliberately or leftover?
- 🔴 **`SQLALCHEMY_DATABASE_URL` bypasses `app/core/config.py`**, read with a bare
  `os.getenv` in `app/db/session.py:8-11`.
- 🟡 **`AeroplaneSchema.wings` is an `OrderedDict` whose first entry is not
  necessarily the main wing.** The main wing is derived as the largest planform
  area (gh-788/gh-1092); consumers must not assume `wings[0]`.
- 🟡 **No uniqueness on `aeroplanes.name`** — duplicate names are possible and
  the `IntegrityError` handler's German "name existiert bereits" message would
  be misleading if raised from a different constraint.
