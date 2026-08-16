# platform-core / background-jobs-invalidation

> Use-case specification. Parent module: [`../requirements.md`](../requirements.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Lifecycle diagram: [`../../state-machines.md`](../../state-machines.md) §7.

## Overview

How an edit becomes recomputed numbers: a synchronous in-process `EventBus`,
four subscriptions registered at startup, and a `JobTracker` that debounces
retrim and assumption-recompute work at 2.0 s per aeroplane. 🟢

Two subtleties dominate this use case. **Marking operating points dirty is done
by the publishers, not the handlers** (BR-82), and **the recompute trigger set
deliberately excludes the parameters the recompute itself writes** (BR-83) —
without that exclusion the system loops forever. 🟢

## Responsibilities

- Provide `EventBus` with `GeometryChanged` and `AssumptionChanged`. 🟢
- Register the four invalidation subscriptions at startup. 🟢
- Provide `mark_ops_dirty` as a bulk status update. 🟢
- Debounce and run retrim and assumption-recompute jobs per aeroplane. 🟢
- Schedule safely from worker threads onto the bound event loop. 🟢
- Shut every job down with the application. 🟢

## Business Rules

- **BR-84 — A broken subscriber can never break the publishing request.** 🟢
  `EventBus.publish` wraps every handler in `try/except` and only logs.
- **BR-PC41 — Two events, both carrying `aeroplane_id` and a UTC timestamp.** 🟢
  `GeometryChanged(+ source_model: "WingModel" | "WingXSecModel" |
  "FuselageModel")` and `AssumptionChanged(+ parameter_name)`.
- **BR-PC42 — Four subscriptions.** 🟢
  | Event | Handler | Guard |
  |---|---|---|
  | `GeometryChanged` | `schedule_retrim` | — |
  | `GeometryChanged` | `schedule_recompute_assumptions` | — |
  | `AssumptionChanged` | `schedule_retrim` | `param ∈ _OP_AFFECTING_PARAMS = {mass, cg_x}` |
  | `AssumptionChanged` | `schedule_recompute_assumptions` | `param ∈ _RECOMPUTE_TRIGGERING_PARAMS = {target_static_margin, mass}` |
- **BR-83 — Recompute triggers exclude their own outputs.** 🟢 `cg_x`, `cd0` and
  `cl_max` are deliberately **not** in `_RECOMPUTE_TRIGGERING_PARAMS`; including
  them would create a `recompute → AssumptionChanged(cg_x) → recompute` loop.
- **BR-82 — Marking dirty and publishing are separate responsibilities.** 🟢/🟡
  `mark_ops_dirty(db, aircraft_id)` is
  `UPDATE operating_points SET status='DIRTY' WHERE aircraft_id = ? AND status
  NOT IN ('DIRTY','COMPUTING')`, and it is called by the **publishers** —
  `mass_cg_service` (×2), `loading_scenario_service`,
  `assumption_compute_service`, `design_assumptions_service` (×2) and the two
  SQLAlchemy listener modules (`models/avl_geometry_events.py:52`,
  `models/stability_events.py:52`) — each immediately **before**
  `event_bus.publish(...)`. The handlers only schedule jobs, yet their log lines
  read *"OPs marked DIRTY"*. 🔴 A new geometry-mutating path that publishes but
  forgets to mark leaves stale operating points with no warning.
- **BR-PC43 — `JobTracker` is a module singleton with two parallel families.** 🟢
  Each is a `dict[aeroplane_id → Job]` plus a `dict[aeroplane_id →
  asyncio.Task]`. Status: `DEBOUNCING → COMPUTING → DONE | FAILED`.
- **BR-PC26 — Create the new task first, then cancel the old.** 🟢
  ```
  new_task = self._create_task_safe(...)
  if new_task is None: return          # nothing was clobbered
  if existing_task and not done: existing_task.cancel()
  self._jobs[id] = Job(...) ; self._debounce_tasks[id] = new_task
  ```
  because `_create_task_safe` can legitimately return `None` (no bound loop,
  unit-test context) and cancelling first would strand the job in `DEBOUNCING`
  with no task to fire it.
- **BR-PC27 — Cross-thread scheduling waits 2.0 s, then gives up silently.** 🟢
  From a worker thread, `_create_task_safe` posts `call_soon_threadsafe` onto
  the bound main loop and waits on a `threading.Event`; on timeout it returns
  `None` and the schedule was dropped with no error — 🟢 it now raises (`R2-11`). A dropped schedule means a recompute or retrim never runs, and nothing recorded it.
- **BR-PC28 — `schedule_retrim`'s short-circuit coalesces rather than drops
  (Q-PC-4).** 🟢 The asymmetry with `schedule_recompute_assumptions` — retrim
  short-circuits while a job is already `COMPUTING`, recompute does not — was a
  **defect**, not a design choice: a retrim requested while one is already
  `COMPUTING` was discarded, so the edit that triggered it might never be
  retrimmed. It compounds with a dropped retrim leaving operating points
  `DIRTY` with nothing left to pick them up (they were absorbing, per
  `Q-AA-6`②). Required: when a job is already running and another request
  arrives, record "re-run needed" and run **once** on completion, rather than
  discarding the request.
- **BR-PC29 — The third job family becomes a tracked `Job` in a service, not a
  `scripts/` import (Q-PC-5).** 🟢
  `schedule_airfoil_low_re_compute(names)` runs a NeuralFoil backfill in a
  worker thread; today it is fire-and-forget with no `Job`, no status, and it
  imports `scripts.backfill_airfoil_low_re._compute_geometry_stats` —
  application code depending on a **private** function of a script — from
  `background_jobs.py:362`. **Required:** the backfill logic moves into a
  service that `background_jobs` calls, and becomes the third of three job
  families to get a `Job` record — closing the one place a background
  operation could fail with no trace.
- **BR-PC44 — The functions are injected, not imported.** 🟢
  `set_trim_function(retrim_dirty_ops)` and
  `set_recompute_function(_recompute_wrapper)` are called in the lifespan, which
  keeps `core/background_jobs.py` free of service imports.
- **BR-PC45 — All state is in memory — permanently, and enforced (Q-CC-8/ADR
  0024).** 🟢 No persistence, no cross-worker sharing, no retry, no dead-letter
  queue. This is a **deliberate, documented architectural constraint**
  following from the single-user, single-worker desktop product position, not
  debt: the application now refuses to start with more than one worker,
  converting the previously silent, data-dependent breakage into a boot
  failure. 🔴 **Still open:** whether a cross-thread schedule dropped after 2 s
  should be surfaced (logged or retried) rather than vanishing — not addressed.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Publish an event to every subscriber, containing handler failures | Must | A raising handler is logged; publish returns normally |
| RF-02 | Register the four subscriptions at startup | Must | Present after the lifespan runs |
| RF-03 | Guard the `AssumptionChanged` subscriptions by parameter set | Must | `cg_x` ⇒ retrim only |
| RF-04 | Exclude `cg_x`, `cd0`, `cl_max` from recompute triggers | Must | No recompute loop |
| RF-05 | Mark operating points dirty in bulk, skipping `DIRTY`/`COMPUTING` | Must | A computing point is not reset |
| RF-06 | Debounce each family at 2.0 s per aeroplane | Must | Two events inside the window ⇒ one run |
| RF-07 | Create the new task before cancelling the old | Must | A `None` task leaves the previous job intact |
| RF-08 | Schedule from a worker thread via the bound loop | Must | `call_soon_threadsafe` + a `threading.Event` |
| RF-09 | Give up after 2.0 s when scheduling cross-thread | Must | 🟡 silently |
| RF-10 | Track status transitions `DEBOUNCING → COMPUTING → DONE\|FAILED` | Must | Observable per aeroplane |
| RF-11 | Record per-job detail for retrim | Should | `dirty_op_ids`, `completed_op_ids`, `failed_op_ids`, timestamps, `error` |
| RF-12 | Short-circuit `schedule_retrim` while `COMPUTING` | Should | Recompute deliberately does not |
| RF-13 | Accept injected trim and recompute functions | Must | No service imports in the module |
| RF-14 | Bind the running loop at startup | Must | Otherwise every schedule is a no-op |
| RF-15 | Shut down cleanly | Must | `await job_tracker.shutdown()` in the lifespan |
| RF-16 | Provide an untracked airfoil low-Re backfill | Could | 🟡 fire-and-forget |

## Non-functional Requirements

| Type | Inferred requirement | Evidence | Confidence |
|------|----------------------|----------|-----------|
| Robustness | A subscriber failure never propagates into a request | `EventBus.publish` | 🟢 |
| Performance | Rapid edits must not trigger a storm of recomputes | `debounce_seconds = 2.0` | 🟢 |
| Performance | CPU-bound recompute runs off the event loop | `_recompute_wrapper`'s `asyncio.to_thread` | 🟢 |
| Correctness | Invalidation must not feed itself | `_RECOMPUTE_TRIGGERING_PARAMS`; BR-83 | 🟢 |
| Correctness | A job must never be cancelled without a replacement | the create-then-cancel order | 🟢 |
| Isolation | The job module must not import services | injected functions | 🟢 |
| Durability | 🟡 Job state does not survive a restart, is not shared across workers, and has no retry or dead-letter path | `background_jobs.py` | 🟡 |
| Reliability | 🟡 A cross-thread schedule can be dropped after 2 s with no signal | `_create_task_safe` | 🟡 |
| Consistency | 🟡 Marking dirty is a manual step every publisher must remember | BR-82 | 🟡 |
| Layering | 🟡 Application code imports from `scripts/` | `background_jobs.py:362` | 🟡 |

## Acceptance Criteria

```gherkin
Feature: The event bus

  Scenario: A broken subscriber is contained
    Given a subscriber that raises
    When GeometryChanged is published
    Then publish returns normally
    And the error is logged

  Scenario: All subscribers run
    Given two subscribers for GeometryChanged
    When it is published
    Then both were called, even if the first raised

Feature: Invalidation routing

  Scenario: Geometry invalidates both families
    When GeometryChanged is published
    Then a retrim and a recompute are both scheduled

  Scenario: cg_x triggers only a retrim
    When AssumptionChanged("cg_x") is published
    Then a retrim is scheduled
    And no recompute is scheduled

  Scenario: mass triggers both
    When AssumptionChanged("mass") is published
    Then both are scheduled

  Scenario: No self-feeding loop
    Given a recompute that writes cg_x, cd0 and cl_max
    When it completes and publishes AssumptionChanged for each
    Then no further recompute is scheduled

  Scenario: Dirty marking skips in-flight points
    Given operating points with statuses TRIMMED, DIRTY and COMPUTING
    When mark_ops_dirty runs
    Then only the TRIMMED one changes to DIRTY

Feature: Debouncing

  Scenario: Coalescing
    Given two GeometryChanged events 0.5 s apart for one aeroplane
    Then exactly one retrim runs, about 2 s after the second

  Scenario: Independent aeroplanes
    Given events for two different aeroplanes
    Then two independent jobs run

  Scenario: Create-before-cancel
    Given an existing debounce task
    When a new schedule is made and task creation fails
    Then the existing task is NOT cancelled
    And the previous job remains DEBOUNCING

  Scenario: Retrim short-circuits while computing
    Given a retrim job in COMPUTING
    When another retrim is scheduled for the same aeroplane
    Then no new debounce task is created

  Scenario: Recompute does not short-circuit
    Given a recompute job in COMPUTING
    When another is scheduled
    Then a new debounce task is created

Feature: Cross-thread scheduling

  Scenario: From a worker thread
    Given a bound main loop
    When schedule_retrim is called from a worker thread
    Then the task is created on the main loop

  Scenario: No bound loop
    Given bind_loop was never called
    Then _create_task_safe returns None
    And the schedule is silently dropped

Feature: Lifecycle

  Scenario: Status transitions
    Then a job goes DEBOUNCING -> COMPUTING -> DONE
    And a raising function ends in FAILED with the error recorded

  Scenario: Shutdown
    When the application shuts down
    Then all debounce tasks are cancelled and shutdown completes
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|---|---|---|
| Event containment (RF-01) | Must | A broken subscriber would otherwise fail user edits |
| The four subscriptions with their guards (RF-02/RF-03) | Must | The whole invalidation contract |
| Excluding recompute outputs (RF-04) | Must | Otherwise the system loops forever |
| Bulk dirty marking that skips in-flight points (RF-05) | Must | Resetting a `COMPUTING` point loses work |
| Debounce (RF-06) | Must | An edit-heavy session would otherwise queue dozens of ASB runs |
| Create-before-cancel (RF-07) | Must | The reverse order strands jobs |
| Loop binding (RF-14) | Must | Without it nothing is ever scheduled |
| Injected functions (RF-13) | Must | Keeps the module free of service imports |
| Clean shutdown (RF-15) | Must | Tasks must not outlive the app |
| Status tracking (RF-10/RF-11) | Should | Drives the UI's recompute-status indicator |
| Retrim short-circuit (RF-12) | Should | A deliberate asymmetry |
| The untracked low-Re backfill (RF-16) | Could | 🟡 fire-and-forget by design |
| Persistence / retry / dead-letter | Won't (today) | 🟡 in-memory only |
| Cross-worker job sharing | Won't (today) | 🟡 per-process |
| A visible error when a cross-thread schedule is dropped | Won't (today) | 🟡 silent |

## Code Traceability

| File | Symbol | Coverage |
|---|---|---|
| `app/core/events.py` | `DomainEvent`, `GeometryChanged`, `AssumptionChanged`, `EventBus`, `event_bus` | 🟢 |
| `app/services/invalidation_service.py` | `register_handlers`, `mark_ops_dirty`, `_OP_AFFECTING_PARAMS`, `_RECOMPUTE_TRIGGERING_PARAMS` | 🟢 |
| `app/core/background_jobs.py` | `JobStatus`, `RetrimJob`, `RecomputeAssumptionsJob`, `JobTracker`, `job_tracker` | 🟢 |
| `…` | `bind_loop`, `set_trim_function`, `set_recompute_function`, `shutdown` | 🟢 |
| `…` | `_create_task_safe` (the 2 s cross-thread timeout) | 🟢 🟡 |
| `…:362` | `schedule_airfoil_low_re_compute` importing from `scripts/` | 🟡 |
| `app/main.py:142-184` | registration + loop binding + function injection | 🟢 |
| `app/main.py:189-196` | teardown | 🟢 |
| `app/models/avl_geometry_events.py:52`, `app/models/stability_events.py:52` | two of the seven `mark_ops_dirty` publishers | 🟢 |
| `app/services/mass_cg_service.py`, `loading_scenario_service.py`, `assumption_compute_service.py`, `design_assumptions_service.py` | the other five publishers | 🟢 owned by their modules |
