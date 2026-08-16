# component-tree-mass-sync — Implementation Tasks

> Executable sequence to re-implement the use case from the legacy behaviour.
> Every task cites the legacy file, a definition of done, and a confidence
> marker. Parent module tasks: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] `design_assumptions` table plus `design_assumptions_service` with
      `update_calculated_value(db, uuid, param, value, source,
      auto_switch_source: bool)` implementing BR-25 — module
      `mission-and-sizing`.
- [ ] `invalidation_service.mark_ops_dirty(db, aeroplane_id)`.
- [ ] `app.core.events` with `event_bus.publish` and the `AssumptionChanged`
      event type.
- [ ] `aggregate_weight_items` — see
      [`../cg-mass-computation/tasks.md`](../cg-mass-computation/tasks.md) T-02.
- [ ] `component_tree_service.get_aircraft_total_weight_kg` returning **`None`**
      for an empty tree — see
      [`../../aeroplane-core/weight-rollup/tasks.md`](../../aeroplane-core/weight-rollup/tasks.md)
      T-05. May be stubbed; the sync must work when it raises.
- [ ] `get_db()` request-scoped session owning the transaction (ADR 0009).

## Tasks

- [ ] **T-01 — The shared five-step skeleton.**
  Implement BR-MB2 once, in both functions, in this exact order: resolve the
  aeroplane → probe for the `"mass"` row (absent ⇒ `return`) → aggregate →
  `update_calculated_value(..., auto_switch_source=True)` → `mark_ops_dirty` +
  publish `AssumptionChanged(mass)`.
  - Legacy origin: `app/services/mass_cg_service.py:131-171` and `:174-221`
  - Definition of done: a test asserts the **order** — nothing is written and no
    event fires when the probe misses; the event fires after, never before, the
    value write.
  - Confidence: 🟢

- [ ] **T-02 — The existence probe.**
  `db.query(DesignAssumptionModel.parameter_name).filter(aeroplane_id == …,
  parameter_name == "mass").first()` — a single-column probe, not a row load.
  `None` ⇒ `return`.
  - Legacy origin: `app/services/mass_cg_service.py:149-158, 189-198`
  - Definition of done: an aircraft with no assumption rows survives both syncs
    with zero writes and zero events; a query counter shows one statement.
  - Confidence: 🟢

- [ ] **T-03 — `sync_weight_items_to_assumptions` (producer A).**
  Load the rows, map them to `WeightItemData` dicts, call
  `aggregate_weight_items`, and **discard all three CG values** (bind them to
  `_cg_x`, `_cg_y`, `_cg_z`). Write with
  `source = "weight_items" if total_mass is not None else None`.
  - Legacy origin: `app/services/mass_cg_service.py:174-221`
  - Definition of done: a test asserts the `cg_x` assumption row is **unchanged
    in every column** after a sync that doubles the mass (guards ADR 0011); a
    second test asserts `calculated_source == "weight_items"`.
  - Confidence: 🟢

- [ ] **T-04 — `sync_component_tree_to_mass` (producer B).**
  Same skeleton with `get_aircraft_total_weight_kg` as the aggregate and
  `source = "component_tree" if total_kg is not None else None`. No CG is
  involved at all.
  - Legacy origin: `app/services/mass_cg_service.py:131-171`
  - Definition of done: a 350 g tree writes `0.35` with source
    `"component_tree"`; an empty tree writes `None`/`None`.
  - Confidence: 🟢

- [ ] **T-05 — The clear-on-empty contract.**
  When the aggregate is `None`, both `calculated_value` and `calculated_source`
  must end up `NULL`, and `effective_value` must fall back to `estimate_value`.
  - Legacy origin: `app/services/mass_cg_service.py:161, 211`
  - Definition of done: a test that fails if either column is written as `0`,
    `0.0` or the previous source string; a follow-up assertion that
    `get_effective_assumption_value(db, uuid, "mass")` returns the estimate.
  - Confidence: 🟢

- [ ] **T-06 — Opt into the auto-switch, do not reimplement it.**
  Pass `auto_switch_source=True` on both calls and let
  `design_assumptions_service` own the "first value only, never a design choice"
  rule (BR-25).
  - Legacy origin: `app/services/mass_cg_service.py:162-169, 212-219`
  - Definition of done: ESTIMATE → CALCULATED on sync 1; after a manual switch
    back to ESTIMATE, sync 2 updates the value but leaves `active_source` at
    ESTIMATE.
  - Confidence: 🟢

- [ ] **T-07 — Function-local imports on both sides.**
  `AssumptionChanged`, `event_bus`, `update_calculated_value`, `mark_ops_dirty`
  and `get_aircraft_total_weight_kg` imported **inside** the sync functions;
  `mass_cg_service` imported **inside** `_sync_aircraft_mass` and
  `_try_sync_assumptions`.
  - Legacy origin: `app/services/mass_cg_service.py:143-146, 207-209`;
    `component_tree_service.py:364`; `weight_items_service.py:60`
  - Definition of done: an import-order test asserts that importing
    `mass_cg_service` pulls in none of `component_tree_service`,
    `design_assumptions_service`, `invalidation_service` or `app.core.events`,
    and that importing `component_tree_service` does not pull in
    `mass_cg_service`.
  - Confidence: 🟢

- [ ] **T-08 — `_sync_aircraft_mass` (tree call site).**
  Bare `except Exception` + `logger.exception`; called from tree create, update,
  delete and move.
  - Legacy origin: `app/services/component_tree_service.py:362-378`
  - Definition of done: with the sync patched to raise `RuntimeError`, all four
    tree write paths still return their success status and persist their change;
    the failure is logged with a traceback.
  - Confidence: 🟢 · owned by `aeroplane-core`; verify from this side as well.

- [ ] **T-09 — `_try_sync_assumptions` (inventory call site).**
  `except (NotFoundError, SQLAlchemyError)` + `logger.warning`; called from
  weight-item create, update and delete.
  - Legacy origin: `app/services/weight_items_service.py:57-64`
  - Definition of done: with the sync patched to raise `SQLAlchemyError`, all
    three writes succeed; with it patched to raise `TypeError`, the write
    **fails** — reproduce the legacy asymmetry, then record it as a gap rather
    than silently widening the catch.
  - Confidence: 🟢

- [ ] **T-10 — Propagation side effects.**
  `mark_ops_dirty(db, aeroplane.id)` then
  `event_bus.publish(AssumptionChanged(aeroplane_id=aeroplane.id,
  parameter_name="mass"))`, in that order, at the end of both syncs — including
  the sync that writes `None`.
  - Legacy origin: `app/services/mass_cg_service.py:170-171, 220-221`
  - Definition of done: spies record exactly one call each per successful sync;
    an empty-producer sync still fires both.
  - Confidence: 🟢

- [ ] **T-11 — No commit, ever.**
  Neither sync calls `db.commit()` or `db.begin()`; both rely on the caller's
  `get_db()` transaction.
  - Legacy origin: ADR 0009, `app/db/session.py:55-64`
  - Definition of done: a test that raises after the CRUD + sync and asserts
    neither the row nor the assumption change is committed.
  - Confidence: 🟢

- [ ] **T-12 — Characterise the producer collision.**
  Do **not** add arbitration — reproduce last-write-wins and pin it with a test
  so any future change is a deliberate one.
  - Legacy origin: `app/services/mass_cg_service.py:162-169` vs `:212-219`
  - Definition of done: sync A → sync B → sync A leaves
    `calculated_source == "weight_items"` and A's value; the test's docstring
    names BR-MB4 and links the open question.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Producer A happy path:** value, source, auto-switch, untouched
      estimate.
- [ ] **TT-02 — Producer B happy path:** 350 g tree ⇒ `0.35` kg with source
      `"component_tree"`.
- [ ] **TT-03 — Unseeded no-op:** no writes, no events, no exception, one query.
- [ ] **TT-04 — Clear-on-empty:** both columns `NULL`; a test fails on `0`/`0.0`.
- [ ] **TT-05 — Auto-switch once:** the manual ESTIMATE choice survives later
      syncs.
- [ ] **TT-06 — `cg_x` immutability:** every column of the `cg_x` row is
      unchanged after a mass sync (ADR 0011 guard).
- [ ] **TT-07 — `estimate_value` immutability** (ADR 0010 guard).
- [ ] **TT-08 — Best-effort, tree path:** patched sync raising `RuntimeError`
      leaves create/update/delete/move all successful.
- [ ] **TT-09 — Best-effort, inventory path:** `SQLAlchemyError` swallowed;
      `TypeError` propagates (characterises the asymmetry).
- [ ] **TT-10 — Event count:** one `AssumptionChanged(mass)` and one
      `mark_ops_dirty` per sync, including the `None`-writing sync.
- [ ] **TT-11 — Event ordering:** the value is written before the event fires.
- [ ] **TT-12 — Import-cycle guards** in both directions.
- [ ] **TT-13 — Transaction atomicity:** a rollback after the sync leaves the
      assumption unchanged in the database.
- [ ] **TT-14 — Producer collision (characterisation):** A → B → A ends on A;
      `calculated_source` names the winner.
- [ ] **TT-15 — Failure after the value write:** patch `mark_ops_dirty` to
      raise and assert the currently-observed outcome (assumption updated,
      operating points not marked) — the test **documents** the gap.

## Data Migration Tasks

- [ ] **TM-01 — Backfill `calculated_source` on legacy rows.** Rows written
      before the source column existed may hold a `calculated_value` with a
      `NULL` source. Decide whether to re-derive it (by checking which producer
      is non-empty) or to leave it `NULL`. 🟢 unblocked — one producer (`Q-MB-1`); the arbitration
      decision below.
- [ ] **TM-02 — No other migration.** The use case owns no table; the three
      columns it writes belong to `design_assumptions` and are created by that
      module's migration. 🟢

## Suggested Order

1. **T-01 → T-02** first: the skeleton and the probe are what make every later
   test safe to run against a fresh aircraft.
2. **T-03** and **T-04** next, in parallel — they are independent and differ
   only in their aggregate and their source label.
3. **T-05 → T-06** immediately after: the `None` contract and the auto-switch
   are the two rules most likely to be broken by a well-meaning simplification,
   so pin them before anything calls the syncs.
4. **T-07** before wiring the call sites — a module-level import here breaks the
   process at startup, so the guard test must exist first.
5. **T-08 → T-09** the two wrappers, developed against syncs patched to raise so
   the best-effort property is proven independently of the happy path.
6. **T-10 → T-11** the side effects and the transaction rule.
7. **T-12** last: it is a characterisation test, and it only makes sense once
   both producers work.

## Pending Gaps (🔴)

- **Which producer wins?** Weight items and the component tree overwrite one
  another's `calculated_value` last-write-wins. Options: explicit per-aircraft
  choice, tree-takes-precedence-when-non-empty, sum both (requires
  double-counting detection), or merge the inventory into the tree.
- **How is double counting detected?** `weight_items` has no `component_id`, so
  the same physical part in both producers is invisible.
- **Should a persistently failing sync be surfaced** to the user rather than
  only logged (ADR 0012 tension)?
- **Should the two wrappers catch the same exception set?** Today a `TypeError`
  fails a weight-item write and not a tree write.
- **Should the event be published on commit rather than inside the
  transaction?** A rollback after a successful sync leaves a published event
  describing a change that never happened.
- **Should a failure between the value write and the event be recoverable?**
  Today the assumption updates and the recompute never fires.
- **Should the tree propagate positions as well as mass**, so an aircraft built
  entirely in the component tree gets an aggregate CG?
- **Should an empty-producer sync skip the recompute?** Clearing the value
  currently triggers the same full downstream chain as setting it.
</content>
