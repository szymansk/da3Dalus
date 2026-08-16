# platform-core / background-jobs-invalidation — Implementation Tasks

> Parent module task list: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] `retrim_service.retrim_dirty_ops` and an assumption-recompute entry point.
- [ ] `operating_points` with a `status` column including `DIRTY` and
      `COMPUTING`.
- [ ] A running asyncio loop at startup (the lifespan binds it).
- [ ] `SessionLocal` for the untracked backfill's own session.

## Tasks

- [ ] **T-01 — `DomainEvent`, `GeometryChanged`, `AssumptionChanged`.**
  Dataclasses with `aeroplane_id` and a UTC `timestamp` default factory; plus
  `source_model` and `parameter_name` respectively.
  - Legacy origin: `app/core/events.py`
  - Definition of done: `source_model` takes `"WingModel"`, `"WingXSecModel"` or
    `"FuselageModel"`; `parameter_name` is a free string matching the assumption
    parameter names.
  - Confidence: 🟢

- [ ] **T-02 — `EventBus`.**
  `dict[type[DomainEvent], list[Callable]]`; `subscribe`; `publish` wrapping
  every handler in `try/except` with `logger.exception`.
  - Legacy origin: `app/core/events.py`
  - Definition of done: a raising handler does not prevent the next handler from
    running and does not propagate to the publisher (BR-84).
  - Confidence: 🟢

- [ ] **T-03 — `mark_ops_dirty`.**
  `UPDATE operating_points SET status='DIRTY' WHERE aircraft_id = ? AND status
  NOT IN ('DIRTY','COMPUTING')`.
  - Legacy origin: `app/services/invalidation_service.py`
  - Definition of done: a `COMPUTING` point is **not** reset — resetting it
    would discard in-flight work.
  - Confidence: 🟢

- [ ] **T-04 — `register_handlers` and the two parameter sets.**
  `_OP_AFFECTING_PARAMS = {"mass", "cg_x"}`;
  `_RECOMPUTE_TRIGGERING_PARAMS = {"target_static_margin", "mass"}`; the four
  subscriptions.
  - Legacy origin: `app/services/invalidation_service.py`
  - Definition of done: `cg_x` schedules a retrim and **no** recompute. **Carry
    the comment** explaining that adding `cg_x`, `cd0` or `cl_max` to the
    recompute set creates a `recompute → AssumptionChanged(cg_x) → recompute`
    loop (BR-83). A test should assert the exclusion explicitly.
  - Confidence: 🟢

- [ ] **T-05 — `JobStatus`, `RetrimJob`, `RecomputeAssumptionsJob`.**
  `DEBOUNCING`, `COMPUTING`, `DONE`, `FAILED`; the retrim job additionally
  carries `dirty_op_ids`, `completed_op_ids`, `failed_op_ids`, `started_at`,
  `finished_at`, `error`.
  - Legacy origin: `app/core/background_jobs.py`
  - Definition of done: the status enum is a `str` enum so it serialises
    directly into the recompute-status endpoint the frontend polls.
  - Confidence: 🟢

- [ ] **T-06 — `JobTracker` state and injection.**
  `debounce_seconds = 2.0`; the four dicts; `_main_loop`; `bind_loop`,
  `set_trim_function`, `set_recompute_function`.
  - Legacy origin: `app/core/background_jobs.py`
  - Definition of done: the module imports **no** service — the functions are
    injected from the lifespan. Without `bind_loop`, every schedule is a no-op;
    assert that.
  - Confidence: 🟢

- [ ] **T-07 — `_create_task_safe`.**
  On the loop → `create_task`; from a worker thread → `call_soon_threadsafe` +
  `threading.Event().wait(timeout=2.0)`; no bound loop or timeout → `None`.
  - Legacy origin: `app/core/background_jobs.py`
  - Definition of done: a call from a worker thread creates the task on the main
    loop. **Reproduce the silent `None` on timeout and record it as a gap** —
    the schedule is lost with no log and no retry.
  - Confidence: 🟢

- [ ] **T-08 — `schedule_retrim` / `schedule_recompute_assumptions`.**
  Retrim short-circuits while `COMPUTING`; recompute does not. Both: create the
  new task **first**, return if it is `None`, only then cancel the old one,
  then store the job and the task.
  - Legacy origin: `app/core/background_jobs.py`
  - Definition of done: a test that swaps the create/cancel order must strand a
    job in `DEBOUNCING` with no task — that failure is the proof the ordering is
    load-bearing. Carry the comment.
  - Confidence: 🟢

- [ ] **T-09 — The debounced runners.**
  `await asyncio.sleep(2.0)`; set `COMPUTING` + `started_at`; call the injected
  function; `DONE` or `FAILED` with `error`; `finished_at` in `finally`.
  - Legacy origin: `app/core/background_jobs.py`
  - Definition of done: two events 0.5 s apart produce exactly one run; a raising
    function ends `FAILED` with the message recorded and **no retry**.
  - Confidence: 🟢

- [ ] **T-10 — `schedule_airfoil_low_re_compute`.**
  A daemon `threading.Thread` running `_run_backfill_for_names`, which owns its
  own session and commits.
  - Legacy origin: `app/core/background_jobs.py:362`
  - Definition of done: reproduced **and recorded as a gap** — it is untracked
    (no `Job`, no status, no shutdown participation) and imports
    `scripts.backfill_airfoil_low_re._compute_geometry_stats` from application
    code.
  - Confidence: 🟢

- [ ] **T-11 — `shutdown`.**
  Cancel every outstanding debounce task, `await asyncio.gather(...,
  return_exceptions=True)`, clear the dicts.
  - Legacy origin: `app/core/background_jobs.py`
  - Definition of done: after shutdown no task remains pending. Note that an
    in-flight worker thread is **not** interruptible.
  - Confidence: 🟢

- [ ] **T-12 — Lifespan wiring.**
  `register_handlers()`, `bind_loop(asyncio.get_running_loop())`,
  `set_trim_function(retrim_dirty_ops)`,
  `set_recompute_function(_recompute_wrapper)`, and `await shutdown()` in the
  `finally`.
  - Legacy origin: `app/main.py:142-196`
  - Definition of done: after startup the tracker has a bound loop and both
    functions; after shutdown no task survives.
  - Confidence: 🟢

### Remediation (behaviour changes — each needs a decision)

- [ ] **T-13 — Make dirty-marking automatic.**
  Move `mark_ops_dirty` into the `GeometryChanged` / `AssumptionChanged`
  handlers so publishing and marking cannot drift apart.
  - Legacy origin: BR-82; the seven publisher call sites
  - Definition of done: a new geometry-mutating path that only publishes still
    ends with dirty operating points. The handler log lines then become true.
  - Confidence: 🟡 (a decision — the handlers currently have no session)

- [ ] **T-14 — Surface a dropped cross-thread schedule.**
  Log (and ideally retry) when `_create_task_safe` times out.
  - Legacy origin: `_create_task_safe`
  - Definition of done: a dropped schedule is visible in the log.
  - Confidence: 🟡 (a decision)

- [ ] **T-15 — Persist job state.**
  Decide whether jobs must survive a restart and be shared across workers.
  - Legacy origin: BR-PC45
  - Definition of done: a restart during `DEBOUNCING` no longer loses the work,
    and two workers report the same job status.
  - Confidence: 🟡 (a decision)

- [ ] **T-16 — Track the low-Re backfill.**
  Give it a `Job`, a status and shutdown participation; move
  `_compute_geometry_stats` out of `scripts/`.
  - Legacy origin: `background_jobs.py:362`
  - Definition of done: application code no longer imports from `scripts/`.
  - Confidence: 🟡 (a decision)

## Test Tasks

- [ ] **TT-01 — Containment:** a raising subscriber is logged; publish returns.
- [ ] **TT-02 — All subscribers run** even when the first raises.
- [ ] **TT-03 — Routing:** `GeometryChanged` ⇒ both; `cg_x` ⇒ retrim only;
      `mass` ⇒ both; `target_static_margin` ⇒ recompute only.
- [ ] **TT-04 — No loop:** a recompute publishing `cg_x`/`cd0`/`cl_max`
      schedules no further recompute.
- [ ] **TT-05 — Dirty marking:** `TRIMMED` → `DIRTY`; `COMPUTING` untouched.
- [ ] **TT-06 — Debounce coalescing:** two events in the window ⇒ one run.
- [ ] **TT-07 — Per-aeroplane isolation:** two aeroplanes ⇒ two jobs.
- [ ] **TT-08 — Create-before-cancel:** with task creation failing, the existing
      task is **not** cancelled (and the swapped-order variant must fail).
- [ ] **TT-09 — Retrim short-circuit:** no new task while `COMPUTING`.
- [ ] **TT-10 — Recompute overlap (characterisation):** a second task **is**
      created while `COMPUTING`.
- [ ] **TT-11 — Cross-thread scheduling:** from a worker thread the task lands
      on the main loop.
- [ ] **TT-12 — No bound loop:** `_create_task_safe` returns `None`; the
      previous job survives.
- [ ] **TT-13 — Status transitions:** `DEBOUNCING → COMPUTING → DONE`, and
      `FAILED` with `error` on a raising function.
- [ ] **TT-14 — Shutdown:** all tasks cancelled, dicts cleared.
- [ ] **TT-15 — Publisher pairing (characterisation):** a path that publishes
      without `mark_ops_dirty` leaves points non-dirty while the handler logs
      "OPs marked DIRTY".

## Suggested Order

1. **T-01 → T-02** the events and the bus: small, pure and independently
   testable.
2. **T-03 → T-04** dirty marking and routing. Write TT-04 (no-loop) early — the
   exclusion set looks arbitrary until a test demonstrates the loop it prevents.
3. **T-05 → T-06** the job types and the tracker's state, with injection so no
   service import creeps in.
4. **T-07 → T-08** task creation and scheduling. TT-08 (the swapped-order
   failure) is the single most valuable test here.
5. **T-09** the debounced runners.
6. **T-10 → T-11** the untracked backfill and shutdown.
7. **T-12** lifespan wiring last — it ties everything to the running loop.
8. **T-13 → T-16** the remediations, in that order: T-13 (atomic marking) has
   the highest correctness value, T-15 (persistence) the largest scope.

## Pending Gaps

- **Should `mark_ops_dirty` move into the handlers**, so publishing and marking
  cannot drift apart (BR-82)? The handlers would need a session.
- **Should a dropped cross-thread schedule be logged or retried** instead of
  vanishing after 2 s?
- **Should job state be persistent and cross-worker?** Today a restart during
  `DEBOUNCING` loses the work and two workers disagree about job status.
- **Should a `FAILED` job be retried**, and should the failure surface anywhere
  beyond the job record?
- **Should recompute short-circuit while `COMPUTING`**, like retrim, or is the
  overlap deliberate?
- **Should a retrim scheduled during `COMPUTING` be queued** rather than
  dropped?
- **Should `schedule_airfoil_low_re_compute` be tracked**, and should
  `_compute_geometry_stats` move out of `scripts/` into the application?
- **Should the handlers' "OPs marked DIRTY" log lines be corrected** while the
  marking still lives in the publishers?
- **Should the 2.0 s debounce be configurable** per family?
