# component-tree

> Use-case specification, nested under the module [`aeroplane-core`](../requirements.md).
> Focuses on WHAT the use case does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: aeroplane-core,
> `_reversa_sdd/data-dictionary.md` §Table `component_tree`.

## Overview

`component-tree` owns the **structure** of the aircraft bill of materials: a
hierarchy of nodes under an aeroplane UUID, with three node types, sibling
ordering by `sort_index`, reparenting with a cycle guard, and a construction-part
field snapshot on create. Weight semantics are deliberately a separate use case
— see [`weight-rollup`](../weight-rollup/requirements.md). 🟢

## Responsibilities

- Read the whole tree for an aeroplane as a nested structure, roots first. 🟢
- Create, partially update and delete nodes of type `group`, `cad_shape` or
  `cots`. 🟢
- Order siblings and roots deterministically by `sort_index`. 🟢
- Assemble the parent/child hierarchy from a flat row set, tolerating orphans. 🟢
- Move a node to a new parent, rejecting any move that would create a cycle. 🟢
- Snapshot `volume_mm3` / `area_mm2` / `material_id` from a referenced
  construction part, without overwriting values the caller supplied explicitly. 🟢
- Expose the group auto-sync hooks that `wing-design` and `fuselage-design` call
  when a wing or fuselage is created or deleted. 🟢

**Explicitly NOT this use case's responsibility:** own-weight resolution, the
roll-up traversal, the aircraft total weight and the mass sync (all →
[`weight-rollup`](../weight-rollup/requirements.md)); aeroplane lifecycle (→
[`aeroplane-crud`](../aeroplane-crud/requirements.md)).

## Business Rules

- **BR-CT1 — Three node types, free-text discriminator.** 🟢 *(refines module
  rule BR-A8.)* `node_type` is `group` (structural), `cad_shape` (Creator output
  or uploaded part) or `cots` (catalogue component). The column is a plain
  `String`, **not** an enum — nothing at the database level rejects a fourth
  value (`app/models/component_tree.py:12-16`).
- **BR-CT2 — Move rejects cycles, and that is the only structural check.** 🟢
  *(refines BR-A11.)* `move_node` walks the ancestor chain of the target parent
  with `_is_descendant`; if the moved node appears, it raises `ValidationError`
  (→ 422) and mutates nothing (`component_tree_service.py:324-325, 339-359`).
  There is no other structural integrity check anywhere in the module.
- **BR-CT3 — The tree tolerates orphans instead of rejecting them.** 🟢
  `_build_tree` is a two-pass assembly: pass 1 builds `id → node`, pass 2
  attaches each node to its `parent_id`. **A node whose parent is not in the map
  becomes a root** rather than being dropped or raising
  (`component_tree_service.py:58-79`).
- **BR-CT4 — Ordering is by `sort_index`, applied to both children and roots.** 🟢
  Sorting happens during assembly, not in the SQL query
  (`component_tree_service.py:58-79`).
- **BR-CT5 — The construction-part snapshot only fills unset fields.** 🟢
  *(refines BR-A14.)* When a node is created with `construction_part_id`,
  `volume_mm3` / `area_mm2` / `material_id` are copied from the referenced part
  **only for fields the caller did not explicitly set**, detected via
  `data.model_dump(exclude_unset=True)`
  (`_snapshot_construction_part_fields:162-187`). An explicitly supplied `None`
  therefore survives, while an omitted field is filled.
- **BR-CT6 — Wings and fuselages auto-sync a tree group.** 🟢 *(refines BR-A15.)*
  Creating a wing or fuselage creates a matching group node; deleting removes
  nodes by the `synced_from` prefix — `wing:<name>` / `fuselage:<name>`
  (`wing_service.create_wing:298-300`,
  `fuselage_service.delete_fuselage:179-181`, gh#108).
- **BR-CT7 — Transactions are owned by `get_db()`.** 🟢 *(refines BR-A16.)* The
  service calls `db.add()` / `db.flush()`, never `db.commit()` or `db.begin()`
  (ADR 0009, `app/db/session.py:55-64`).
- **BR-CT8 — Node identity is the integer `id`; aeroplane identity is a UUID
  string.** 🟢 Routes address nodes by `{node_id}` (integer) under an
  `{aeroplane_id}` (UUID).
- 🟢 **`component_tree.aeroplane_id` becomes a real foreign key** to
  `aeroplanes.uuid` (`Q-CC-7`, maintainer-answered). It is one of three tables
  migrated to real FKs — motivated not by PostgreSQL but by a defect present
  today under SQLite: deleting an aeroplane leaves its tree rows behind, invisible
  because no aeroplane resolves them, while still occupying the index.
- 🟢 **Read-side depth limiting is added, reported as a `DesignWarning`**
  (`Q-AC-3`, maintainer-answered). `_build_tree` turns orphans into roots and
  `_roll_up_weights` recurses infinitely on a cycle, so a cycle arriving
  out-of-band — direct SQL, an import, a future bulk endpoint — **hangs every
  read** of that aeroplane. The `move_node` write guard alone is not the intended
  level of protection.
- 🟢 **Deleting a node that has children is rejected** (`Q-AC-10`,
  maintainer-answered, option c). **This is a behaviour change, not a
  confirmation of the cascade.** Today the subtree disappears because of the
  SQLAlchemy relationship cascade and nothing in the service intends it; from now
  on `delete_component` raises a `ConflictError` → **409** naming how many
  children block it, and the caller removes them first. See RF-12.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-09 | Read the component tree for an aeroplane as a nested structure *(module RF-09; the computed weight fields it also carries belong to `weight-rollup`)* | Must | `GET .../component-tree` → 200 with roots first and children nested under their parent |
| RF-10 | Add a node of type `group` / `cad_shape` / `cots` *(module RF-10)* | Must | `POST .../component-tree` → 201 with the node id; ordering respects `sort_index` |
| RF-11 | Update a node partially *(module RF-11)* | Must | `PUT .../component-tree/{node_id}` → 200; fields absent from the payload are untouched |
| RF-12 | Delete a **leaf** node; reject deletion of a node that has children *(module RF-12)* | Must | `DELETE .../component-tree/{node_id}` on a childless node → 200; on a node with children → **409**, naming the blocking child count (`Q-AC-10`) |
| RF-13 | Move a node to a new parent, rejecting a move into its own descendant *(module RF-13)* | Must | `POST .../component-tree/move` with a descendant target → 422; a valid move → 200 |
| RF-15 | Snapshot `volume_mm3` / `area_mm2` / `material_id` from a referenced construction part without overwriting explicitly supplied values *(module RF-15)* | Should | Create a node with `construction_part_id` **and** an explicit `volume_mm3`; the explicit value survives while `area_mm2` is filled from the part |
| RF-17 | Auto-create and remove a group when a wing or fuselage is created or deleted *(module RF-17)* | Should | After `PUT .../wings/{name}` a group node with `synced_from = "wing:<name>"` exists; after `DELETE` it is gone |
| RF-CT-18 | Order siblings and roots deterministically by `sort_index` | Must | Two siblings with `sort_index` 1 and 0 are returned in the order 0, 1 |
| RF-CT-19 | Tolerate a node whose parent row is missing by promoting it to a root | Should | A node pointing at a deleted parent still appears in the response, as a root |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Performance | The tree is loaded in a single query for the aeroplane UUID and assembled in memory, not walked with per-node queries | `app/services/component_tree_service.py:123-160` | 🟢 |
| Performance | `aeroplane_id` is indexed so the whole-tree lookup is one indexed scan | `app/models/component_tree.py` (indexed String column) | 🟢 |
| Correctness | A reparent that would create a cycle is rejected before any mutation | `component_tree_service.py:324-325, 339-359` | 🟢 |
| Correctness | A partial update must not clear fields the caller omitted — `exclude_unset` semantics | `component_tree_service.py:162-187` | 🟢 |
| Robustness | Tree assembly never raises on inconsistent `parent_id` data; orphans degrade to roots | `component_tree_service.py:58-79` | 🟢 |
| Reliability | The transaction boundary is the request; a rejected move leaves no partial write | `app/db/session.py:55-64` (ADR 0009) | 🟢 |
| Security | No application-level authentication; the deployment tunnel is the trust boundary | ADR 0016 | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Reading the tree

  Scenario: The tree is returned nested and ordered
    Given an aeroplane with a root group G and two children ordered by sort_index 1 then 0
    When I GET /aeroplanes/{id}/component-tree
    Then the response status is 200
    And G appears as a root
    And G's children are returned in sort_index order 0 then 1

  Scenario: An orphaned node is promoted to a root
    Given a node whose parent_id points at a row that no longer exists
    When I GET /aeroplanes/{id}/component-tree
    Then the node appears in the response
    And it appears as a root rather than being dropped

  Scenario: Reading the tree of an unknown aeroplane
    Given no aeroplane with the requested UUID
    When I GET /aeroplanes/{id}/component-tree
    Then the response status is 404
    And the error code is "not_found"

Feature: Node CRUD

  Scenario: Adding a group node
    Given an aeroplane with an empty component tree
    When I POST a node with node_type "group" and no parent_id
    Then the response status is 201
    And the response carries the new node id
    And the node appears as a root on the next read

  Scenario: A partial update leaves omitted fields untouched
    Given a node with quantity 4 and weight_override_g 120
    When I PUT that node with only quantity 6
    Then the response status is 200
    And quantity is 6
    And weight_override_g is still 120

  Scenario: Deleting a node that has children is rejected
    Given a group G with two child nodes
    When I DELETE G
    Then the response status is 409
    And the error names the blocking child count
    And G and both children still remain

  Scenario: Deleting a leaf node succeeds
    Given a group G with two child nodes
    When I DELETE each child, then G
    Then every response status is 200
    And neither G nor its children remain

  Scenario: Updating a node that does not exist
    Given no node with id 999999 for this aeroplane
    When I PUT /aeroplanes/{id}/component-tree/999999
    Then the response status is 404
    And the error code is "not_found"

Feature: Moving a node

  Scenario: A valid move reparents the node
    Given root groups A and B, where A has no relationship to B
    When I POST a move of A with new parent B
    Then the response status is 200
    And A appears as a child of B on the next read

  Scenario: Moving a node into its own descendant is rejected
    Given node A with descendant B
    When I POST a move of A with new parent B
    Then the response status is 422
    And the error code is "validation_error"
    And the tree is unchanged

Feature: Construction-part snapshot

  Scenario: Omitted metrics are filled from the referenced part
    Given a construction part with volume_mm3 1500 and area_mm2 900
    When I create a node referencing that part without supplying volume_mm3 or area_mm2
    Then the node's volume_mm3 is 1500
    And its area_mm2 is 900

  Scenario: An explicitly supplied metric survives the snapshot
    Given a construction part with volume_mm3 1500
    When I create a node referencing that part with an explicit volume_mm3 of 2000
    Then the node's volume_mm3 is 2000
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Tree read with nesting and ordering (RF-09, RF-CT-18) | Must | Every consumer — the workbench BoM view and `weight-rollup` — starts from this structure |
| Node CRUD (RF-10…RF-12) | Must | The only way to author the bill of materials |
| Move with the cycle guard (RF-13, BR-CT2) | Must | The single structural integrity check; without it the read-time recursion is unbounded |
| Orphan tolerance (RF-CT-19, BR-CT3) | Should | Deliberate robustness, but the tree remains usable if orphans were rejected instead |
| Construction-part snapshot (RF-15) | Should | Convenience copy — the caller may always supply the values explicitly |
| Wing/fuselage group auto-sync (RF-17) | Should | UX convenience (gh#108); the tree is authorable without it |
| Read-time depth limiting with a `DesignWarning` | **Must** | 🟢 decided (`Q-AC-3`) — a cycle arriving out-of-band hangs every read; not yet implemented |
| `node_type` CHECK constraint | **Must** | 🟢 decided (`Q-CC-9`) — `component_tree.node_type` is one of the genuinely closed columns receiving a DB CHECK; NULLs backfilled first |
| FK from `component_tree.aeroplane_id` to `aeroplanes.uuid` | **Must** | 🟢 decided (`Q-CC-7`) — migrated to a real FK now, under SQLite, to stop orphaned rows; previously recorded as migration decision, not a behaviour this spec can assume |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/api/v2/endpoints/aeroplane/component_tree.py` | GET/POST ``, PUT/DELETE `/{node_id}`, POST `/move` (l.52-128) | 🟢 |
| `app/services/component_tree_service.py` | `get_tree` (l.123), `_build_tree` (l.58-79), `move_node` (l.324), `_is_descendant` (l.339-359), `_snapshot_construction_part_fields` (l.162-187) | 🟢 |
| `app/models/component_tree.py` | `ComponentTreeNodeModel` (l.12-16) | 🟢 |
| `app/services/wing_service.py` | `create_wing` group auto-sync (l.298-300) | 🟢 |
| `app/services/fuselage_service.py` | `delete_fuselage` synced-node removal (l.179-181) | 🟢 |
| `app/db/session.py` | `get_db` transaction boundary (l.55-64) | 🟢 |
