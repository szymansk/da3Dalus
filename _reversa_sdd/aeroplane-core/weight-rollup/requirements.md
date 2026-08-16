# weight-rollup

> Use-case specification, nested under the module [`aeroplane-core`](../requirements.md).
> Focuses on WHAT the use case does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: aeroplane-core,
> `_reversa_sdd/data-dictionary.md` §Table `component_tree`, ADR 0012.

## Overview

`weight-rollup` turns the component-tree **structure** into a **mass**: it
resolves each node's own weight through a strict precedence chain, sums the tree
post-order into `total_weight_g` with a three-valued `weight_status`, reports the
aircraft total in kilograms, and pushes that number into the mass model as a
fire-and-forget side effect. It is the bottom-up counterpart to the top-down
`total_mass_kg` design target. 🟢

## Responsibilities

- Resolve a node's own weight and its provenance label through the precedence
  chain `override → cots → calculated → none`. 🟢
- Compute the CAD-shape mass from material density, using the volume or surface
  print formula. 🟢
- Roll weights up the tree post-order into `total_weight_g`. 🟢
- Classify every node with a `weight_status` of `valid` / `partial` / `invalid`. 🟢
- Report the aircraft total weight in kilograms, or `null` for an empty tree. 🟢
- Pre-compute all own weights before the recursion so the traversal issues no
  queries. 🟢
- Push the tree weight into `mass_cg_service` without ever failing the CRUD call
  that triggered it. 🟢

**Explicitly NOT this use case's responsibility:** node CRUD, ordering, move and
the tree assembly (all → [`component-tree`](../component-tree/requirements.md));
the design `total_mass_kg` target (→
[`aeroplane-crud`](../aeroplane-crud/requirements.md)); CG and mass physics
(→ module `mass-and-balance`).

## Business Rules

- **BR-WR1 — Own-weight resolution is a strict precedence chain.** 🟢 *(refines
  module rule BR-A9.)* First match wins, and each branch also fixes the reported
  `weight_source` (`_calculate_own_weight:461-474`):

  ```
  1. weight_override_g is not None -> (weight_override_g, "override")
  2. node_type == "cots"           -> (component.mass_g * quantity, "cots")
  3. CAD shape with a material density -> ( calculated , "calculated")
  4. otherwise                     -> (None, "none")
  ```

- **BR-WR2 — Two print formulas, one default.** 🟢 The `calculated` branch
  (l.442-458) selects on `print_type`:

  ```
  surface print:  area_mm2   * print_resolution_mm * density_kg_m3 / 1e6 * scale_factor
  volume  print:  volume_mm3                       * density_kg_m3 / 1e6 * scale_factor

  print_resolution_mm defaults to 0.4
  ```

  The `/ 1e6` factor converts mm³ × kg/m³ into grams. Result unit: **grams**.
- **BR-WR3 — Weight roll-up is post-order and status-aware.** 🟢 *(refines
  BR-A10.)* `_roll_up_weights:82-120`:

  ```
  total_weight_g(node) = (own_weight_g or 0) + Σ total_weight_g(children)

  weight_status:
    leaf      -> "valid"   if own source != "none" else "invalid"
    non-leaf  -> all children valid   -> "valid"
                 all children invalid -> "partial" if own weight present else "invalid"
                 mixed                -> "partial"
  ```

- **BR-WR4 — A missing weight contributes zero to the sum but degrades the
  status.** 🟢 `own_weight_g` of `None` is treated as `0` inside the arithmetic,
  so a total is always a number; the honesty of that number is carried by
  `weight_status`, not by the total.
- **BR-WR5 — An empty tree yields `None`, not `0`.** 🟢 *(refines BR-A12.)*
  `get_aircraft_total_weight_kg:381-403` returns `None` for an empty tree so the
  caller can **clear** the mass `calculated_value` instead of writing a
  fabricated zero. Consistent with ADR 0012 — design warnings, not silent
  fallbacks.
- **BR-WR6 — Mass sync is fire-and-forget.** 🟢 *(refines BR-A13.)*
  `_sync_aircraft_mass:362-378` lazy-imports
  `mass_cg_service.sync_component_tree_to_mass` and swallows every exception; a
  failed mass sync must never block tree CRUD. The lazy import exists to break
  the `component_tree_service ↔ mass_cg_service` import cycle.
- **BR-WR7 — Own weights are pre-computed before the recursion.** 🟢 `get_tree`
  builds one `id → (grams, source)` dict up front (l.133-137) so
  `_roll_up_weights` issues no further queries. The traversal is therefore O(N)
  in memory and O(1) in SQL statements.
- **BR-WR8 — `total_weight_g` and `weight_status` are computed, never
  persisted.** 🟢 They exist only in the response; only the inputs
  (`weight_override_g`, `component_id`, `quantity`, `volume_mm3`, `area_mm2`,
  `material_id`, `print_type`, `print_resolution_mm`, `scale_factor`) are stored.
- **BR-WR9 — Grams inside the tree, kilograms at the aircraft boundary.** 🟢
  Every node-level weight field is in **grams**; `get_aircraft_total_weight_kg`
  divides by 1000 and is the only kilogram-valued output of this use case.
- 🟢 **Read-side depth limiting is added, reported as a `DesignWarning`**
  (`Q-AC-3`, maintainer-answered). `_roll_up_weights` recurses infinitely on a
  cycle introduced out-of-band, and the `move_node` write guard
  ([`component-tree`](../component-tree/requirements.md)) is explicitly **not**
  the intended level of protection on its own.
- 🟢 **Negative `scale_factor` and `quantity` are rejected at the schema**
  (`Q-AC-4`, maintainer-answered). They are not a deliberate "credit"
  affordance — nothing in the own-weight chain rejects them today and they would
  **subtract** from the aircraft total.
- 🟡 **A COTS node with a missing `component_id` or a component without
  `mass_g` falls through to `"none"`**, degrading the parent to `partial` rather
  than raising — inferred from the strict first-match-wins structure of the
  chain.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-09 | Decorate every node in the tree read with `own_weight_g`, `weight_source`, `total_weight_g` and `weight_status` *(module RF-09)* | Must | `GET .../component-tree` → 200; a parent's `total_weight_g` equals own + Σ children |
| RF-14 | Report the aircraft total weight in kg from the tree, or `null` for an empty tree *(module RF-14)* | Must | `GET .../component-tree/weight` → 200; empty tree ⇒ `total_weight_kg == null`; a 350 g tree ⇒ `0.35` |
| RF-16 | Propagate tree weight changes into the mass model without ever failing the CRUD call *(module RF-16)* | Should | Force `mass_cg_service` to raise; the tree write still returns its success status |
| RF-WR-20 | Resolve own weight through the documented precedence chain, reporting the matching `weight_source` | Must | A node with both `weight_override_g` and a COTS `component_id` reports `override` and the override value |
| RF-WR-21 | Compute a CAD-shape mass from material density using the print-type-specific formula | Must | A volume print of 1 000 000 mm³ at 1 200 kg/m³ with `scale_factor` 1.0 yields 1 200 g |
| RF-WR-22 | Default `print_resolution_mm` to 0.4 for surface prints when unset | Must | A surface print with no `print_resolution_mm` computes as if 0.4 were supplied |
| RF-WR-23 | Classify each node as `valid` / `partial` / `invalid` per the status ladder | Must | A parent with one valid and one `none`-source child reports `partial` |
| RF-WR-24 | Issue a constant number of SQL statements for a tree of N nodes | Should | A query counter over a 50-node tree read shows no growth with N |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Performance | The weight roll-up must not issue N queries — own weights are pre-computed into one dict before the recursion | `app/services/component_tree_service.py:133-137` | 🟢 |
| Availability | The mass sync on tree writes is best-effort: failures are logged, never propagated | `component_tree_service.py:362-378` | 🟢 |
| Maintainability | The `component_tree_service ↔ mass_cg_service` import cycle is broken by a lazy import inside the function rather than by restructuring | `component_tree_service.py:362-378` | 🟢 |
| Correctness | An absent aggregate is reported as `null`, never as a fabricated `0`, so the caller can distinguish "no data" from "zero mass" | `component_tree_service.py:381-403`; ADR 0012 | 🟢 |
| Correctness | Node weights are grams throughout; only the aircraft-level accessor converts to kilograms | `component_tree_service.py:381-403` | 🟢 |
| Reliability | The transaction boundary is the request; a failed sync leaves no partial write | `app/db/session.py:55-64` (ADR 0009) | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Own-weight precedence

  Scenario: An override beats every other source
    Given a cots node with component mass_g 250, quantity 2 and weight_override_g 90
    When the tree is read
    Then the node's own_weight_g is 90
    And its weight_source is "override"

  Scenario: A cots node multiplies component mass by quantity
    Given a cots node referencing a component of mass_g 250 with quantity 2
    And no weight_override_g
    When the tree is read
    Then the node's own_weight_g is 500
    And its weight_source is "cots"

  Scenario: A node with no usable source reports none
    Given a group node with no override, no component and no material
    When the tree is read
    Then the node's own_weight_g is null
    And its weight_source is "none"

Feature: Calculated CAD-shape weight

  Scenario: A volume print is computed from volume and density
    Given a cad_shape node with print_type "volume", volume_mm3 1000000,
      a material of density_kg_m3 1200 and scale_factor 1.0
    When the tree is read
    Then own_weight_g is 1200
    And weight_source is "calculated"

  Scenario: A surface print defaults the resolution to 0.4 mm
    Given a cad_shape node with print_type "surface", area_mm2 500000,
      no print_resolution_mm, a material of density_kg_m3 1200 and scale_factor 1.0
    When the tree is read
    Then own_weight_g equals 500000 * 0.4 * 1200 / 1e6
    And weight_source is "calculated"

Feature: Roll-up and status

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
    And G.total_weight_g is 100

  Scenario: A parent whose children are all invalid but which has its own weight
    Given a group node G with weight_override_g 60 and two children whose weight source is "none"
    When I GET /aeroplanes/{id}/component-tree
    Then G.weight_status is "partial"

  Scenario: A parent with no own weight and only invalid children is invalid
    Given a group node G with no own weight and two children whose weight source is "none"
    When I GET /aeroplanes/{id}/component-tree
    Then G.weight_status is "invalid"

Feature: Aircraft total weight

  Scenario: The total is reported in kilograms
    Given a tree whose roots sum to 350 g
    When I GET /aeroplanes/{id}/component-tree/weight
    Then total_weight_kg is 0.35

  Scenario: An empty tree reports no weight rather than zero
    Given an aeroplane with no component-tree nodes
    When I GET /aeroplanes/{id}/component-tree/weight
    Then total_weight_kg is null

Feature: Fire-and-forget mass sync

  Scenario: A failing mass sync does not fail the write
    Given mass_cg_service.sync_component_tree_to_mass raises an exception
    When I POST a new component-tree node
    Then the response status is 201
    And the node is persisted
    And the failure is logged
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Own-weight precedence chain (RF-WR-20, BR-WR1) | Must | Every downstream weight number derives from it; a wrong precedence silently changes the aircraft mass |
| Roll-up and status ladder (RF-09, RF-WR-23) | Must | The tree's whole purpose — and `weight_status` is the only signal that a total is incomplete |
| Calculated CAD-shape formulas (RF-WR-21, RF-WR-22) | Must | The 3D-printed parts have no other mass source; the 0.4 mm default is load-bearing |
| Aircraft total with `null` semantics (RF-14, BR-WR5) | Must | Drives the mass assumption's `calculated_value`; a fabricated `0` would be indistinguishable from a real empty aircraft |
| Query-count guarantee (RF-WR-24, BR-WR7) | Should | A performance property of the existing design; correctness does not depend on it |
| Fire-and-forget mass sync (RF-16, BR-WR6) | Should | Improves consistency, but is deliberately non-blocking and therefore not on the critical path |
| Read-time depth limiting with a `DesignWarning` | **Must** | 🟢 decided (`Q-AC-3`) — a cycle hangs every read of the affected aeroplane; not yet implemented |
| Persisting `total_weight_g` / `weight_status` | Won't | Deliberately computed at read time; persisting them would create a staleness class that does not exist today |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/api/v2/endpoints/aeroplane/component_tree.py` | GET `/weight` (l.52-128) | 🟢 |
| `app/services/component_tree_service.py` | `_calculate_own_weight` (l.461-474), the COTS branch (l.432-439), the calculated branch (l.442-458), `_roll_up_weights` (l.82-120), own-weight pre-computation (l.133-137), `get_aircraft_total_weight_kg` (l.381-403), `_sync_aircraft_mass` (l.362-378) | 🟢 |
| `app/models/component_tree.py` | `ComponentTreeNodeModel` weight-bearing columns | 🟢 |
| `app/services/mass_cg_service.py` | `sync_component_tree_to_mass` | 🟡 called via a lazy import; contract owned by `mass-and-balance` |
| `app/db/session.py` | `get_db` transaction boundary (l.55-64) | 🟢 |
