# component-tree-mass-sync

> Use-case specification, nested under the module
> [`mass-and-balance`](../requirements.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Sources: `app/services/mass_cg_service.py:131-221`,
> `app/services/component_tree_service.py:362-403`,
> `app/services/weight_items_service.py:57-64`, ADR 0010, ADR 0011, ADR 0012.
> The component tree's own roll-up is specified in
> [`../../aeroplane-core/weight-rollup/design.md`](../../aeroplane-core/weight-rollup/design.md).

## Overview

Two independent bottom-up mass producers — the **weight-item inventory** and the
**component tree** — write the same `mass` design assumption. This use case is
the pair of sync functions that carry a producer's aggregate into
`design_assumptions."mass".calculated_value`, flip the source to CALCULATED the
first time, and publish the event that makes the rest of the system recompute.
🟢

It is deliberately best-effort in both directions: a broken sync must never
block the edit that triggered it, and an aircraft whose assumptions have not
been seeded yet must not blow up on its first weight item. 🟢

## Responsibilities

- `sync_weight_items_to_assumptions` — aggregate the inventory and write the
  calculated mass with source `"weight_items"`. 🟢
- `sync_component_tree_to_mass` — take the tree roll-up and write the calculated
  mass with source `"component_tree"`. 🟢
- Auto-switch `active_source` to CALCULATED on the first value. 🟢
- Clear both `calculated_value` and `calculated_source` when the producing
  source becomes empty. 🟢
- Mark operating points dirty and publish `AssumptionChanged(mass)` on every
  sync. 🟢
- Deliberately **not** write `cg_x`. 🟢

**NOT this use case:** the weight ladder and the tree traversal
(→ [`../../aeroplane-core/weight-rollup`](../../aeroplane-core/weight-rollup/requirements.md)),
the inventory CRUD (→ [`../weight-items`](../weight-items/requirements.md)), the
assumption table and `update_calculated_value` itself
(→ `mission-and-sizing`), and the retrim chain that consumes the event
(→ `aero-analysis`).

## Business Rules

> Global ids from [`../../domain.md`](../../domain.md); `BR-MB*` from
> [`../requirements.md`](../requirements.md); `BR-SY*` are new here.

- **BR-MB2 — Both syncs share one five-step shape.** 🟢
  ```
  1. aeroplane = _get_aeroplane(db, uuid)          -> NotFoundError
  2. probe design_assumptions WHERE parameter_name = "mass"
     absent -> return                              (no-op, not an error)
  3. aggregate                                     -> total_kg | None
  4. update_calculated_value(db, uuid, "mass", total_kg, source,
                             auto_switch_source=True)
  5. mark_ops_dirty(db, aeroplane.id)
     event_bus.publish(AssumptionChanged(aeroplane_id, "mass"))
  ```
  (`mass_cg_service.py:131-171` and `:174-221`.)
- **BR-MB1 — Step 2 makes the sync safe on an unseeded aircraft.** 🟢 The probe
  selects only `DesignAssumptionModel.parameter_name`, so it is a cheap
  existence check, and its `None` result returns without touching anything.
- **BR-MB3 — The source label follows the value, not the trigger.** 🟢
  `source = "<producer>" if total is not None else None`. An emptied producer
  therefore writes `calculated_value = None` **and** `calculated_source = None`
  — the assumption falls back to its estimate rather than claiming a 0 kg
  aircraft.
- **BR-29 / BR-MB5 — `None`, never `0.0`.** 🟢 `get_aircraft_total_weight_kg`
  returns `None` for an empty tree and `aggregate_weight_items` returns `None`
  for an empty inventory, precisely so step 4 can clear the value (ADR 0011 §5,
  ADR 0012).
- **BR-25 — Auto-switch happens once.** 🟢 Both calls pass
  `auto_switch_source=True`, which flips `active_source` from ESTIMATE to
  CALCULATED **only** on the first calculated value. A user who switches back to
  ESTIMATE keeps that choice through later syncs. The docstring states the UX
  intent: *"Mass is always calculated from the component tree by default … users
  who want a manual override can flip the source back to ESTIMATE"*
  (`:174-186`).
- **BR-28 — `cg_x` is never written (ADR 0011).** 🟢
  `sync_weight_items_to_assumptions` computes all three CG axes and binds them
  to `_cg_x`, `_cg_y`, `_cg_z` (`:205`) — the underscore prefix is the code's
  own statement that the values are discarded on purpose. gh-465.
- **BR-SY1 — Step 5 is what makes a mass edit propagate.** 🟢
  `mark_ops_dirty` invalidates the operating points; `AssumptionChanged(mass)`
  drives retrim and the V_stall recompute in `assumption_compute_service`. Both
  fire on **every** sync, including one that writes `None`. 🟡 An
  empty-producer sync therefore triggers a full downstream recompute.
- **BR-SY2 — Every collaborator is imported inside the function.** 🟢
  `AssumptionChanged`, `event_bus`, `update_calculated_value`, `mark_ops_dirty`
  and `get_aircraft_total_weight_kg` are all function-local imports
  (`:143-146, 207-209`), breaking the
  `mass_cg_service ↔ component_tree_service` and
  `mass_cg_service ↔ design_assumptions_service` cycles.
- **BR-30 — Neither call site lets the sync fail its CRUD.** 🟢
  `component_tree_service._sync_aircraft_mass` catches bare `Exception` and logs
  with `logger.exception`; `weight_items_service._try_sync_assumptions` catches
  `(NotFoundError, SQLAlchemyError)` and logs a warning. 🟡 The two catches are
  **not** symmetric — an unexpected exception type fails a weight-item write but
  not a tree write.
- **BR-MB4 — 🟢 One producer: the component tree** (`Q-MB-1`). Previously two, last-write-wins: There is no
  arbitration, no precedence and no warning. An aircraft with both a populated
  inventory and a populated tree ends with whichever was touched last;
  `calculated_source` is the only record of the winner.
- **BR-SY3 — The tree sync carries mass only, never position.** 🟢
  `get_aircraft_total_weight_kg` returns a scalar; the tree's `pos_x/y/z`
  columns never reach the mass/CG layer. 🟡 `Q-MB-4` routes the CG comparison through the tree. Consequence: an aircraft built
  entirely in the component tree has a known mass and **no** aggregate CG, so
  [`cg-mass-computation`](../cg-mass-computation/requirements.md)'s comparison
  returns `null`.
- **BR-78 / ADR 0009 — No commit.** 🟢 The sync runs inside the caller's
  transaction; a rollback undoes the CRUD write and the assumption write
  together.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Write the weight-item aggregate into `mass.calculated_value` with source `"weight_items"` | Must | After a weight-item create the row holds `Σ mᵢ` and `calculated_source == "weight_items"` |
| RF-02 | Write the component-tree roll-up into the same field with source `"component_tree"` | Must | After a tree write the row holds the kg total and `calculated_source == "component_tree"` |
| RF-03 | Return silently when the aeroplane has no `"mass"` assumption row | Must | An unseeded aircraft: the sync creates nothing and raises nothing |
| RF-04 | Raise `NotFoundError` for an unknown aeroplane UUID | Must | The caller's best-effort wrapper converts it into a logged warning |
| RF-05 | Clear value **and** source when the producer is empty | Must | Deleting the last weight item ⇒ `calculated_value == null` and `calculated_source == null` |
| RF-06 | Auto-switch `active_source` to CALCULATED on the first value only | Must | ESTIMATE → CALCULATED on sync 1; a manual switch back to ESTIMATE survives sync 2 |
| RF-07 | Never modify `estimate_value` | Must | The estimate is byte-identical before and after any sync |
| RF-08 | Never modify `cg_x` | Must | The `cg_x` row is byte-identical after a sync that changes the mass by 100 % |
| RF-09 | Mark operating points dirty on every sync | Must | A spy on `mark_ops_dirty` records one call per sync |
| RF-10 | Publish exactly one `AssumptionChanged(mass)` per sync | Must | An event-bus spy records one event, with `parameter_name == "mass"` |
| RF-11 | Run inside the caller's transaction without committing | Must | A rollback after the CRUD undoes the assumption write too |
| RF-12 | Survive the tree service raising | Must | With `get_aircraft_total_weight_kg` patched to raise, the tree CRUD still returns its success status |
| RF-13 | Survive the assumption service raising | Should | With `update_calculated_value` patched to raise `SQLAlchemyError`, the weight-item write still returns 201 |
| RF-14 | Break the import cycles with function-local imports | Must | Importing `mass_cg_service` at module load must not import `component_tree_service`, `design_assumptions_service` or `invalidation_service` |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Availability | A mass-sync failure degrades the assumption, never the edit that triggered it | `component_tree_service.py:362-378`, `weight_items_service.py:57-64` | 🟢 |
| Correctness | An empty producer clears the calculation instead of asserting 0 kg | `mass_cg_service.py:161, 211`; ADR 0012 | 🟢 |
| Correctness | The design CG survives every mass sync untouched (ADR 0011) | `:182-186, 205` | 🟢 |
| Correctness | The user's manual `active_source` choice is respected after the first auto-switch (BR-25) | `auto_switch_source=True` semantics in `design_assumptions_service` | 🟢 |
| Reliability | The sync shares the caller's transaction, so partial state cannot commit | ADR 0009, `app/db/session.py:55-64` | 🟢 |
| Maintainability | Cycles are broken by function-local imports rather than a mediator module | `:143-146, 207-209` | 🟢 |
| Performance | The weight-item sync is one indexed query plus an O(n) sum; the tree sync delegates to a query-free roll-up | `:200-205`; `component_tree_service.py:133-137` | 🟢 |
| Observability | A swallowed failure leaves a log line and nothing else — no counter, no user-visible signal | `logger.exception` / `logger.warning` | 🔴 |

## Acceptance Criteria

```gherkin
Feature: Weight items drive the mass assumption

  Scenario: The first sync switches the source
    Given a seeded aeroplane whose mass assumption is ESTIMATE 1.5 kg
    When a weight item of 0.8 kg is created
    Then mass.calculated_value is 0.8
    And mass.calculated_source is "weight_items"
    And mass.active_source is "CALCULATED"
    And mass.estimate_value is still 1.5

  Scenario: Emptying the inventory clears the calculation
    Given an aeroplane whose only weight item is 0.8 kg and whose mass is CALCULATED
    When that weight item is deleted
    Then mass.calculated_value is null
    And mass.calculated_source is null

  Scenario: A manual switch back to ESTIMATE survives later syncs
    Given an aeroplane whose mass was auto-switched to CALCULATED
    And the user switched active_source back to ESTIMATE
    When another weight item is added
    Then mass.calculated_value is updated
    And mass.active_source is still "ESTIMATE"

Feature: The component tree drives the same assumption

  Scenario: A tree write publishes its own source
    Given an aeroplane with a component tree totalling 350 g
    When the tree is mutated
    Then mass.calculated_value is 0.35
    And mass.calculated_source is "component_tree"

  Scenario: An empty tree clears the calculation
    Given an aeroplane whose component tree has no nodes
    When the tree sync runs
    Then mass.calculated_value is null
    And a test fails if it is 0 or 0.0

Feature: Safety properties

  Scenario: An unseeded aircraft is a silent no-op
    Given an aeroplane with no design_assumptions rows
    When either sync runs
    Then no row is created
    And no exception is raised

  Scenario: The design CG is never touched
    Given an aeroplane whose cg_x assumption is 0.150 m
    When the mass is synced from 1.5 kg to 3.0 kg
    Then the cg_x row is unchanged in every column

  Scenario: A failing sync does not fail the tree CRUD
    Given mass_cg_service.sync_component_tree_to_mass raises RuntimeError
    When a component-tree node is created
    Then the response status is 201
    And the node is persisted
    And the failure is logged

  Scenario: A failing sync does not fail the weight-item CRUD
    Given sync_weight_items_to_assumptions raises SQLAlchemyError
    When a weight item is created
    Then the response status is 201
    And a warning is logged

Feature: Propagation

  Scenario: Every sync publishes exactly one event
    Given a seeded aeroplane
    When a weight item is created, updated and deleted in turn
    Then exactly three AssumptionChanged(mass) events are published
    And mark_ops_dirty is called three times

  Scenario: An empty-producer sync still propagates
    Given an aeroplane whose last weight item is being deleted
    When the sync writes a null calculated value
    Then AssumptionChanged(mass) is still published
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Both syncs writing the calculated side (RF-01/RF-02) | Must | The `mass` assumption feeds retrim, V_stall, the matching chart, endurance and the powertrain solution space |
| Unseeded no-op (RF-03) | Must | Without it, the very first weight item on a new aircraft would 500 |
| Clear-on-empty (RF-05) | Must | ADR 0011 §5 — a fabricated 0 kg aircraft would corrupt every downstream sizing surface |
| Auto-switch once (RF-06) | Must | The documented UX contract; switching on every sync would override the user's manual choice |
| `estimate_value` / `cg_x` immutability (RF-07/RF-08) | Must | ADR 0010 and ADR 0011 respectively; violating either inverts the design loop |
| Event + dirty marking (RF-09/RF-10) | Must | The only propagation mechanism; a missed event leaves the whole aircraft stale |
| Best-effort behaviour (RF-12/RF-13) | Must | An explicit design property with a documented trade-off (BR-30) |
| Transaction sharing (RF-11) | Must | ADR 0009 |
| Import-cycle guard (RF-14) | Must | Both cycles are real; a module-level import breaks the process at startup |
| Symmetric exception handling between the two call sites | Should | 🟡 currently asymmetric; the narrow catch can still fail a weight-item write |
| Arbitration between producers | **N/A** | 🟢 only one producer remains (`Q-MB-1`); not implemented — last-write-wins is the current contract |
| Position/CG propagation from the tree | **Should** | 🟢 consumed by `Q-MB-3`/`Q-MB-4`; the tree publishes mass only |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/mass_cg_service.py:131-171` | `sync_component_tree_to_mass` | 🟢 |
| `app/services/mass_cg_service.py:174-221` | `sync_weight_items_to_assumptions` | 🟢 |
| `app/services/mass_cg_service.py:78-97` | `aggregate_weight_items` (step 3 of producer A) | 🟢 |
| `app/services/component_tree_service.py:362-378` | `_sync_aircraft_mass` — call site B | 🟢 owned by `aeroplane-core` |
| `app/services/component_tree_service.py:381-403` | `get_aircraft_total_weight_kg` — aggregate B | 🟢 owned by `aeroplane-core` |
| `app/services/weight_items_service.py:57-64` | `_try_sync_assumptions` — call site A | 🟢 |
| `app/services/design_assumptions_service` | `update_calculated_value(auto_switch_source=True)` | 🟢 owned by `mission-and-sizing` |
| `app/services/invalidation_service` | `mark_ops_dirty` | 🟢 owned by `mission-and-sizing` |
| `app/core/events` | `event_bus`, `AssumptionChanged` | 🟢 owned by `platform-core` |
</content>
