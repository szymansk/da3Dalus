# aeroplane-core

> Module-level specification. Focuses on WHAT the module does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: aeroplane-core,
> `_reversa_sdd/data-dictionary.md` §Module: aeroplane-core, `_reversa_sdd/domain.md` §1.1/§2.

## Overview

`aeroplane-core` owns the **`Aeroplane` aggregate root** — the single entity every
other module hangs off. It provides aircraft CRUD, the design total mass, the
hierarchical component tree (bill of materials with weight roll-up), and the
assembly of wings + fuselages into the CAD-side `AirplaneConfiguration` export
payload. Since gh-903 every aeroplane is *also* a node in a versioning lineage,
so creation is never a single-row insert. 🟢

## Responsibilities

- Create, list, read, and delete aeroplanes, addressed publicly by **UUID**. 🟢
- Bootstrap the versioning lineage (root + `main` branch) on every create. 🟢
- Serve the full nested read model (`AeroplaneSchema`: wings + fuselages + mass
  + reference point) in one call. 🟢
- Store and serve the design total mass (`total_mass_kg`) as an upsert. 🟢
- Own the **component tree** — node CRUD, moves, and the post-order weight
  roll-up that yields the aircraft's bottom-up mass. 🟢
- Assemble the CAD export payload `AirplaneConfiguration` and guarantee it is
  JSON-serialisable (no NumPy leakage). 🟢
- Translate domain exceptions into the HTTP error contract. 🟢

**Explicitly NOT this module's responsibility:** wing/fuselage geometry semantics
(→ `wing-design`, `fuselage-design`), mass/CG physics (→ `mass-and-balance`),
branch/snapshot operations beyond the birth of the lineage (→ `versioning`).

## Business Rules

- **BR-A1 — Every new aeroplane is born as a complete versioning node.** 🟢
  `create_aeroplane` performs a three-step flush dance to satisfy the circular
  `aeroplanes ↔ branches` FK pair: insert aeroplane → `flush()` to obtain the id
  → set `root_id = self.id` → create `BranchModel(root_id=id, head_id=id,
  name="main", is_main=True, created_by="human")` → `flush()` → back-fill
  `aeroplane.branch_id`. (`app/services/aeroplane_service.py:75-100`)
- **BR-A2 — Exactly one main branch per lineage.** 🟢 Enforced at DDL level by the
  partial unique index `uq_branches_one_main_per_root`
  (`app/models/aeroplanemodel.py:616-624`). The FK circularity is resolved with
  `use_alter=True` on both sides (`:629-638, :691-706`).
- **BR-A3 — Eager materialisation before serialisation.** 🟢 `get_aeroplane_schema`
  walks `wing.x_secs → detail → spares / trailing_edge_device.servo_data` purely
  to force the lazy loads *inside* the session, because FastAPI serialises the
  response after the `get_db()` generator has closed
  (`app/services/aeroplane_service.py:141-149`). This is a deliberate
  workaround, **not** dead code — removing it produces `DetachedInstanceError`.
- **BR-A4 — `AirplaneConfiguration` export requires a mass.** 🟢 A missing
  `total_mass_kg` raises `ValidationError` → HTTP 422 *before* any conversion is
  attempted (`app/services/aeroplane_service.py:263-267`).
- **BR-A5 — No NumPy in the CAD payload.** 🟢 `_to_json_compatible` recursively
  converts `np.ndarray` → `list` and `np.generic` → Python scalars
  (`aeroplane_service.py:33-44`).
- **BR-A6 — Delete is cascade + best-effort side effect.** 🟢 The ORM cascade
  removes wings, fuselages, weight items, assumptions, copilot messages,
  scenarios and stability results; afterwards
  `openvsp_step_export_service.cleanup_aeroplane_step_files()` runs in a bare
  `try/except` that only logs (`aeroplane_service.py:191-198`) — orphaned STEP
  files are tolerated rather than blocking the delete.
- **BR-A7 — `GET /aeroplanes` hides snapshots by default.** 🟢 `heads_only: bool =
  True` lists only branch-head nodes so immutable version snapshots stay out of
  the picker (`app/api/v2/endpoints/aeroplane/base.py:78-95`).
- **BR-A8 — Three component-tree node types.** 🟢 `group` (structural),
  `cad_shape` (Creator output or uploaded part), `cots` (catalogue component).
  Free-text discriminator column, no enum (`app/models/component_tree.py:12-16`).
- **BR-A9 — Own-weight resolution is a strict precedence chain.** 🟢
  `weight_override_g` → COTS `component.mass_g × quantity` → CAD-shape density
  calculation → `(None, "none")`
  (`component_tree_service._calculate_own_weight:461-474`).
- **BR-A10 — Weight roll-up is post-order and status-aware.** 🟢
  `total_weight_g(node) = own + Σ children`; the `weight_status` ladder is
  `valid` / `partial` / `invalid` as defined in `design.md`
  (`component_tree_service._roll_up_weights:82-120`).
- **BR-A11 — Move rejects cycles.** 🟢 `move_node` refuses a move whose new parent
  is a descendant of the moved node (`_is_descendant`, `:324-325, :339-359`).
  This is the **only** structural integrity check in the module.
- **BR-A12 — An empty tree yields `None`, not `0`.** 🟢
  `get_aircraft_total_weight_kg` returns `None` for an empty tree so the caller
  can *clear* the mass `calculated_value` instead of writing a fabricated zero
  (`:381-403`). Consistent with ADR 0012 (design warnings, not silent
  fallbacks).
- **BR-A13 — Mass sync is fire-and-forget.** 🟢 `_sync_aircraft_mass` lazy-imports
  `mass_cg_service.sync_component_tree_to_mass` and swallows every exception —
  a failed mass sync must never block tree CRUD (`:362-378`, documented in the
  docstring).
- **BR-A14 — Construction-part snapshot only fills unset fields.** 🟢 When a node
  is created with `construction_part_id`, `volume_mm3` / `area_mm2` /
  `material_id` are copied from the referenced part **only for fields the caller
  did not explicitly set**, detected via `data.model_dump(exclude_unset=True)`
  (`_snapshot_construction_part_fields:162-187`).
- **BR-A15 — Wings and fuselages auto-sync a tree group.** 🟢 Creating a wing or
  fuselage creates a matching component-tree group; deleting removes nodes by
  the `synced_from` prefix (`wing:<name>` / `fuselage:<name>`)
  (`wing_service.create_wing:298-300`, `fuselage_service.delete_fuselage:179-181`,
  gh#108).
- **BR-A16 — Transactions are owned by `get_db()`.** 🟢 Services call
  `db.flush()` / `db.add()` but never `db.commit()` / `db.begin()`
  (ADR 0009, `app/db/session.py:55-64`).
- 🔴 **No cycle detection on the component tree at read time.** `_build_tree`
  makes orphans into roots; `_roll_up_weights` would recurse infinitely on a
  cycle introduced out-of-band. Only `move_node` guards writes.
- 🔴 **`component_tree.aeroplane_id` is a plain indexed `String`, not a foreign
  key** to `aeroplanes.uuid` — deleting an aeroplane does not cascade to its
  tree nodes.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | List all aeroplanes ordered by `name`; `heads_only=true` (default) restricts the result to branch-head nodes | Must | `GET /aeroplanes` returns 200 with `aeroplanes[]`; a snapshot node created by `versioning` is absent unless `heads_only=false` |
| RF-02 | Create an aeroplane by name and return its UUID, atomically creating the lineage root and the `main` branch | Must | `POST /aeroplanes` → 201; the new row has `root_id == id`, `branch_id` set, and exactly one `branches` row with `is_main=true` |
| RF-03 | Read the full nested aircraft (wings, fuselages, mass, `xyz_ref`) by UUID | Must | `GET /aeroplanes/{id}` → 200 `AeroplaneSchema` with every nested spar/TED/servo populated; unknown UUID → 404 |
| RF-04 | Delete an aeroplane, cascading all owned rows, and attempt STEP artefact cleanup | Must | `DELETE /aeroplanes/{id}` → 200; the aeroplane and all children are gone; a cleanup failure does **not** fail the request |
| RF-05 | Read the design total mass | Must | `GET /aeroplanes/{id}/total_mass_kg` → 200 with `total_mass_kg`; unknown UUID → 404 |
| RF-06 | Upsert the design total mass, distinguishing create from update by status code | Must | First `POST .../total_mass_kg` → **201**, subsequent → **200** |
| RF-07 | Assemble and return the `AirplaneConfiguration` CAD payload | Must | `GET .../airplane_configuration` → 200 with a JSON-serialisable body containing no NumPy types |
| RF-08 | Reject the `AirplaneConfiguration` export when `total_mass_kg` is unset | Must | Aeroplane without mass → 422 `validation_error` |
| RF-09 | Read the component tree with computed roll-up weights and per-node `weight_status` | Must | `GET .../component-tree` → 200; a parent's `total_weight_g` equals own + Σ children |
| RF-10 | Add a component-tree node of type `group` / `cad_shape` / `cots` | Must | `POST .../component-tree` → 201 with the node id; ordering respects `sort_index` |
| RF-11 | Update a component-tree node (partial) | Must | `PUT .../component-tree/{node_id}` → 200; unset fields are untouched |
| RF-12 | Delete a component-tree node (and its subtree, per cascade) | Must | `DELETE .../component-tree/{node_id}` → 200; children are removed |
| RF-13 | Move a node to a new parent, rejecting a move into its own descendant | Must | `POST .../component-tree/move` with a descendant target → 422; valid move → 200 |
| RF-14 | Report the aircraft total weight in kg from the tree, or `null` for an empty tree | Must | `GET .../component-tree/weight` → 200; empty tree ⇒ `total_weight_kg == null` |
| RF-15 | Snapshot `volume_mm3` / `area_mm2` / `material_id` from a referenced construction part, without overwriting explicitly supplied values | Should | Create a node with `construction_part_id` and an explicit `volume_mm3`; the explicit value survives |
| RF-16 | Propagate tree weight changes into the mass model without ever failing the CRUD call | Should | Force `mass_cg_service` to raise; the tree write still returns 200 |
| RF-17 | Auto-create/remove a component-tree group when a wing or fuselage is created/deleted | Should | After `PUT .../wings/{name}` a group node with `synced_from = "wing:<name>"` exists |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Correctness | Response serialisation must not touch a closed session — nested relations are pre-materialised inside the request scope | `app/services/aeroplane_service.py:141-149` | 🟢 |
| Correctness | The CAD payload must be free of NumPy scalars/arrays before it leaves the service | `aeroplane_service.py:33-44` | 🟢 |
| Correctness | Exactly one `is_main` branch per lineage, enforced in the schema, not only in code | `app/models/aeroplanemodel.py:616-624` | 🟢 |
| Performance | The weight roll-up must not issue N queries — own weights are pre-computed into one dict before the recursion | `component_tree_service.py:133-137` | 🟢 |
| Availability | Artefact cleanup on delete and mass sync on tree writes are best-effort: failures are logged, never propagated | `aeroplane_service.py:191-198`, `component_tree_service.py:362-378` | 🟢 |
| Reliability | Transaction boundary is the request; a handler raising after partial writes leaves no committed partial state | `app/db/session.py:55-64` (ADR 0009) | 🟢 |
| Reliability | SQLite runs WAL + `synchronous=NORMAL` + `busy_timeout=30000` because assumption recompute holds a write transaction for seconds | `app/db/session.py:15-52` | 🟢 |
| Security | No application-level authentication; the deployment tunnel is the trust boundary | ADR 0016 | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Aeroplane lifecycle

  Scenario: Creating an aeroplane also creates its lineage
    Given an empty database
    When I POST /aeroplanes with name "Trainer 1"
    Then the response status is 201
    And the response contains a UUID
    And the stored row has root_id equal to its own id
    And exactly one branches row exists with name "main", is_main true and created_by "human"

  Scenario: Reading an unknown aeroplane
    Given no aeroplane with UUID "00000000-0000-0000-0000-000000000000"
    When I GET /aeroplanes/00000000-0000-0000-0000-000000000000
    Then the response status is 404
    And the error code is "not_found"

  Scenario: Listing hides immutable snapshots by default
    Given a lineage whose head has one immutable predecessor snapshot
    When I GET /aeroplanes
    Then only the head node is listed
    When I GET /aeroplanes?heads_only=false
    Then both nodes are listed

Feature: Total mass upsert

  Scenario: First write creates
    Given an aeroplane without total_mass_kg
    When I POST /aeroplanes/{id}/total_mass_kg with 2.4
    Then the response status is 201

  Scenario: Second write updates
    Given an aeroplane with total_mass_kg 2.4
    When I POST /aeroplanes/{id}/total_mass_kg with 2.6
    Then the response status is 200
    And the stored total_mass_kg is 2.6

Feature: AirplaneConfiguration export

  Scenario: Export succeeds for a fully specified aircraft
    Given an aeroplane with total_mass_kg 2.4, one wing and one fuselage
    When I GET /aeroplanes/{id}/airplane_configuration
    Then the response status is 200
    And the payload is JSON-serialisable with no numpy types

  Scenario: Export refuses without a mass
    Given an aeroplane whose total_mass_kg is null
    When I GET /aeroplanes/{id}/airplane_configuration
    Then the response status is 422
    And the error code is "validation_error"

Feature: Component tree

  Scenario: Weight rolls up post-order
    Given a group node G with two cots children of 100 g and 250 g
    And G has no own weight
    When I GET /aeroplanes/{id}/component-tree
    Then G.total_weight_g is 350
    And G.weight_status is "valid"

  Scenario: A child without a weight source degrades the parent
    Given a group node G with one valid 100 g child and one child whose weight source is "none"
    When I GET /aeroplanes/{id}/component-tree
    Then G.weight_status is "partial"

  Scenario: Moving a node into its own descendant is rejected
    Given node A with descendant B
    When I POST /aeroplanes/{id}/component-tree/move with node A and new parent B
    Then the response status is 422
    And the tree is unchanged

  Scenario: Empty tree reports no weight rather than zero
    Given an aeroplane with no component-tree nodes
    When I GET /aeroplanes/{id}/component-tree/weight
    Then total_weight_kg is null
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Aeroplane CRUD by UUID (RF-01…RF-04) | Must | Critical path — every other module resolves an aeroplane first |
| Lineage bootstrap on create (BR-A1/BR-A2) | Must | Without it `versioning`, `ai-copilot` and the comparison UI have no anchor; the partial index makes a wrong write impossible to repair silently |
| Nested read model with eager materialisation (RF-03) | Must | The frontend workbench loads the aircraft in one call; the lazy-load workaround has no fallback |
| Total-mass upsert (RF-05/RF-06) | Must | Gate for the CAD export and input to `mass-and-balance` |
| `AirplaneConfiguration` export + mass gate (RF-07/RF-08) | Must | The only handover into the CAD stack |
| Component-tree CRUD + roll-up (RF-09…RF-14) | Must | Sole bottom-up mass producer alongside `weight_items`; drives the mass assumption's `calculated_value` |
| Move-node cycle guard (RF-13) | Must | The only structural integrity check; without it the read path recurses infinitely |
| Construction-part snapshot (RF-15) | Should | Convenience copy — the caller may always supply the values explicitly |
| Fire-and-forget mass sync (RF-16) | Should | Improves consistency, but is deliberately non-blocking and therefore not on the critical path |
| Wing/fuselage group auto-sync (RF-17) | Should | UX convenience (gh#108); the tree is usable without it |
| Read-time cycle/depth defence | Could | 🔴 not implemented; only reachable via out-of-band writes |
| `app/api/v2/endpoints/aeroplane.py` legacy router | Won't | Dead code — shadowed by the package of the same name, never imported |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/api/v2/endpoints/aeroplane/base.py` | 7 routes + `_raise_http_from_domain` | 🟢 |
| `app/api/v2/endpoints/aeroplane/component_tree.py` | 6 routes (l.52-128) | 🟢 |
| `app/services/aeroplane_service.py` | `list_all_aeroplanes`, `create_aeroplane`, `get_aeroplane_by_uuid`, `get_aeroplane_schema`, `delete_aeroplane`, `get_aeroplane_mass`, `set_aeroplane_mass`, `get_aeroplane_airplane_configuration`, `_to_json_compatible` | 🟢 |
| `app/services/component_tree_service.py` | `get_tree`, `_build_tree`, `_roll_up_weights`, `_calculate_own_weight`, `move_node`, `_is_descendant`, `get_aircraft_total_weight_kg`, `_sync_aircraft_mass`, `_snapshot_construction_part_fields` | 🟢 |
| `app/models/aeroplanemodel.py` | `AeroplaneModel`, `BranchModel` | 🟢 |
| `app/models/component_tree.py` | `ComponentTreeNodeModel` | 🟢 |
| `app/schemas/aeroplaneschema.py` | `AeroplaneSchema` | 🟢 |
| `app/api/v2/endpoints/aeroplane.py` | legacy router module | 🔴 dead — never imported |
