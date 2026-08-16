# platform-core / background-jobs-invalidation — Technical Design

> Use-case design. Parent module: [`../design.md`](../design.md).
> Lifecycle diagram: [`../../state-machines.md`](../../state-machines.md) §7.

## Interface

### `app/core/events.py` (49 l.) 🟢

```python
@dataclass
class DomainEvent:
    aeroplane_id: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class GeometryChanged(DomainEvent):   source_model: str    # WingModel|WingXSecModel|FuselageModel
@dataclass
class AssumptionChanged(DomainEvent): parameter_name: str  # mass|cg_x|cl_max|...

class EventBus:
    _handlers: dict[type[DomainEvent], list[Callable]]
    def subscribe(self, event_type, handler) -> None
    def publish(self, event) -> None      # try/except per handler, logs only

event_bus = EventBus()                    # module singleton
```

### `app/services/invalidation_service.py` 🟢

```python
_OP_AFFECTING_PARAMS         = {"mass", "cg_x"}
_RECOMPUTE_TRIGGERING_PARAMS = {"target_static_margin", "mass"}
def register_handlers() -> None
def mark_ops_dirty(db, aircraft_id) -> None
```

### `app/core/background_jobs.py` (431 l.) 🟢

```python
class JobStatus(str, Enum): DEBOUNCING; COMPUTING; DONE; FAILED

@dataclass
class RetrimJob:  aeroplane_id; status; dirty_op_ids: list[int]
                  completed_op_ids; failed_op_ids; started_at; finished_at; error
@dataclass
class RecomputeAssumptionsJob: aeroplane_id; status; started_at; finished_at; error

class JobTracker:
    debounce_seconds = 2.0
    _jobs / _recompute_jobs:                     dict[int, Job]
    _debounce_tasks / _recompute_debounce_tasks: dict[int, asyncio.Task]
    _trim_function / _recompute_function:        Callable[[int], Awaitable[None]] | None
    _main_loop:                                  asyncio.AbstractEventLoop | None

    def bind_loop(loop) / set_trim_function(fn) / set_recompute_function(fn)
    def schedule_retrim(aeroplane_id) / schedule_recompute_assumptions(aeroplane_id)
    def schedule_airfoil_low_re_compute(names: list[str])     # untracked 🔴
    async def shutdown()

job_tracker = JobTracker()                # module singleton
```

## Main Flow

### F1 — Publish 🟢

```python
def publish(self, event):
    for handler in self._handlers.get(type(event), []):
        try:    handler(event)
        except Exception:
            logger.exception("event handler failed for %s", type(event).__name__)
```

Synchronous and in-process: the publishing request pays the cost of every
handler, which is acceptable only because the handlers **only schedule** — they
never compute. 🟢

### F2 — Registration 🟢

```python
def register_handlers():
    event_bus.subscribe(GeometryChanged,   lambda e: job_tracker.schedule_retrim(e.aeroplane_id))
    event_bus.subscribe(GeometryChanged,   lambda e: job_tracker.schedule_recompute_assumptions(e.aeroplane_id))
    event_bus.subscribe(AssumptionChanged, lambda e: e.parameter_name in _OP_AFFECTING_PARAMS
                                                     and job_tracker.schedule_retrim(e.aeroplane_id))
    event_bus.subscribe(AssumptionChanged, lambda e: e.parameter_name in _RECOMPUTE_TRIGGERING_PARAMS
                                                     and job_tracker.schedule_recompute_assumptions(e.aeroplane_id))
```

`_RECOMPUTE_TRIGGERING_PARAMS` excludes `cg_x`, `cd0` and `cl_max` **because the
recompute writes them**. The comment says so, and the omission is the only thing
preventing an infinite `recompute → AssumptionChanged(cg_x) → recompute`
loop. 🟢 (BR-83)

### F3 — The split responsibility 🟢/🔴

```
publisher (7 call sites):
    mark_ops_dirty(db, aircraft_id)          # UPDATE ... SET status='DIRTY'
                                             # WHERE aircraft_id = ? AND status NOT IN ('DIRTY','COMPUTING')
    event_bus.publish(GeometryChanged(...))  # -> handlers only SCHEDULE

handler:
    job_tracker.schedule_retrim(id)
    logger.info("OPs marked DIRTY ...")      # 🔴 describes work the CALLER already did
```

The seven publishers: `mass_cg_service` (×2), `loading_scenario_service`,
`assumption_compute_service`, `design_assumptions_service` (×2), plus the
SQLAlchemy listener modules `models/avl_geometry_events.py:52` and
`models/stability_events.py:52`.

🟡 A new geometry-mutating path that publishes but forgets to mark leaves stale
operating points, and the log will still claim they were marked.

### F4 — Scheduling 🟢

```python
def schedule_retrim(self, aeroplane_id):
    job = self._jobs.get(aeroplane_id)
    if job and job.status == JobStatus.COMPUTING:
        return                                    # short-circuit — retrim ONLY

    new_task = self._create_task_safe(self._debounced_retrim(aeroplane_id))
    if new_task is None:
        return                                    # nothing was clobbered
    existing = self._debounce_tasks.get(aeroplane_id)
    if existing and not existing.done():
        existing.cancel()                         # cancel ONLY after the replacement exists
    self._jobs[aeroplane_id] = RetrimJob(aeroplane_id, JobStatus.DEBOUNCING, ...)
    self._debounce_tasks[aeroplane_id] = new_task
```

`schedule_recompute_assumptions` is identical **without** the `COMPUTING`
short-circuit. 🟢

```python
async def _debounced_retrim(self, aeroplane_id):
    await asyncio.sleep(self.debounce_seconds)    # 2.0 — a new schedule cancels this
    job.status = COMPUTING ; job.started_at = now
    try:    await self._trim_function(aeroplane_id)
            job.status = DONE
    except Exception as exc:
            job.status = FAILED ; job.error = str(exc)
    finally: job.finished_at = now
```

### F5 — Cross-thread task creation 🟢

```python
def _create_task_safe(self, coro):
    try:
        loop = asyncio.get_running_loop()         # we ARE on the loop
        return loop.create_task(coro)
    except RuntimeError:
        pass                                      # a worker thread

    if self._main_loop is None:
        return None                               # unit-test context — no loop bound

    holder, done = {}, threading.Event()
    def _make_task():
        holder["task"] = self._main_loop.create_task(coro)
        done.set()
    self._main_loop.call_soon_threadsafe(_make_task)
    if not done.wait(timeout=2.0):
        return None                               # 🔴 SILENTLY dropped
    return holder["task"]
```

This path exists because the recompute pipeline runs inside
`asyncio.to_thread`, and a service running there may itself publish an event. 🟢

### F6 — The third job family becomes tracked 🟢 (`Q-PC-5`)

```python
def schedule_airfoil_low_re_compute(self, names: list[str]):
    threading.Thread(target=self._run_backfill_for_names, args=(names,), daemon=True).start()

def _run_backfill_for_names(self, names):
    from scripts.backfill_airfoil_low_re import _compute_geometry_stats   # l.362 🔴
    db = SessionLocal()
    try: ... ; db.commit()          # one of the four legitimate own-session paths
    finally: db.close()
```

No `Job`, no status, no cancellation, no shutdown participation — and
application code importing from `scripts/`. 🔴

### F7 — Shutdown 🟢

```python
async def shutdown(self):
    for task in list(self._debounce_tasks.values()) + list(self._recompute_debounce_tasks.values()):
        if not task.done(): task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    self._debounce_tasks.clear() ; self._recompute_debounce_tasks.clear()
```

Called from the lifespan's `finally` (`main.py:192`). A job already in
`COMPUTING` inside a worker thread is not interruptible. 🟡

## Alternative Flows

- **No bound loop** (unit tests): every schedule is a no-op; the previous job is
  left untouched thanks to the create-before-cancel order. 🟢
- **Cross-thread schedule times out after 2 s:** 🟢 fails loudly, as `bind_loop` does (`R2-11`, `Q-PC-7`, `Q-CC-8`).
- **A retrim is scheduled while one is `COMPUTING`:** ignored; the edit that
  triggered it will not be retrimmed until something schedules again. 🟡
- **A recompute is scheduled while one is `COMPUTING`:** a second debounce task
  is created, so two recomputes can overlap for one aeroplane. 🟡
- **The trim/recompute function raises:** status `FAILED`, `error` recorded, no
  retry. 🔴
- **Shutdown during `COMPUTING`:** the debounce task is cancelled; an in-flight
  worker thread runs to completion or dies with the process. 🟡
- **Process restart:** all job state is lost — a `DEBOUNCING` job never
  fires. 🔴
- **Two worker processes:** each has its own `JobTracker`, so the UI's job
  status depends on which worker answered. 🔴
- **A publisher forgets `mark_ops_dirty`:** points stay `TRIMMED` while the
  geometry has changed; the retrim then finds nothing dirty to do. 🔴

## Dependencies

- `asyncio` (tasks, `sleep`, `call_soon_threadsafe`, `gather`), `threading`
  (`Thread`, `Event`).
- `retrim_service.retrim_dirty_ops` and the lifespan's `_recompute_wrapper` —
  both **injected**, never imported here.
- `db.session.SessionLocal` for the untracked backfill.
- `scripts.backfill_airfoil_low_re` 🔴.
- The seven publishers that call `mark_ops_dirty`.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| A synchronous in-process bus, because handlers only schedule | `events.py` | 🟢 |
| Contain every handler exception | `publish`'s `try/except` | 🟢 |
| Guard `AssumptionChanged` subscriptions by parameter set | `invalidation_service` | 🟢 |
| Exclude the recompute's own outputs from its triggers | `_RECOMPUTE_TRIGGERING_PARAMS` comment; BR-83 | 🟢 |
| Debounce per aeroplane at 2.0 s | `debounce_seconds` | 🟢 |
| Create the new task before cancelling the old | the ordering comment | 🟢 |
| Short-circuit retrim but not recompute while computing | the two schedule methods | 🟢 (a 🟡 asymmetry) |
| Inject the trim/recompute functions to avoid service imports | `set_*_function` | 🟢 |
| Bridge worker threads with `call_soon_threadsafe` + an `Event` | `_create_task_safe` | 🟢 |
| Accept a 2 s cap on that bridge and drop the schedule on timeout | `done.wait(timeout=2.0)` | 🟢 (a 🟡 silent loss) |
| Keep all job state in memory | the two dicts | 🟢 (a 🟡 durability gap) |
| Let publishers mark dirty rather than the handlers | seven call sites; BR-82 | 🟡 |

## Internal State

| State | Where | Lifecycle |
|---|---|---|
| `event_bus._handlers` | `core/events.py` | populated once in the lifespan |
| `_jobs` / `_recompute_jobs` | `JobTracker` | per aeroplane; overwritten by the next schedule; **lost on restart** 🟡 |
| `_debounce_tasks` / `_recompute_debounce_tasks` | `JobTracker` | cancelled and replaced per schedule; cleared on shutdown |
| `_main_loop` | `JobTracker` | bound once in the lifespan |
| `_trim_function` / `_recompute_function` | `JobTracker` | injected once in the lifespan |
| the low-Re backfill thread | a bare `threading.Thread` | untracked, daemon 🟡 |

## Observability

- `logger.exception` from `EventBus.publish` when a handler raises. 🟢
- `JobTracker` logs schedule / start / finish per family. 🟢
- 🔴 The handlers log *"OPs marked DIRTY"* although the **publisher** did the
  marking — actively misleading.
- 🔴 A dropped cross-thread schedule logs nothing.
- 🔴 No metric for queue depth, debounce-coalescing rate, job duration or
  failure rate.
- 🔴 The untracked backfill has no status at all.

## Risks and Gaps

- 🔴 **All job state is in memory and per-process** — no persistence, no retry,
  no dead-letter, no cross-worker sharing. A restart during `DEBOUNCING` loses
  the work silently.
- 🔴 **A cross-thread schedule can be dropped after 2 s** with no error, no log
  and no retry.
- 🟡 **Marking dirty and publishing are not atomic** (BR-82). `Q-PC-4` fixes the related short-circuit by coalescing rather than dropping; atomicity itself was not put to the maintainer. Seven publishers
  must remember both halves, and the handler's log line claims credit for work
  it did not do.
- 🔴 **`schedule_airfoil_low_re_compute` is fire-and-forget** and imports from
  `scripts/` inside application code.
- 🔴 **A `FAILED` job is never retried** and nothing surfaces the failure beyond
  the job record.
- 🟡 **Recompute can overlap itself** for one aeroplane, since only retrim
  short-circuits on `COMPUTING`.
- 🟡 **A retrim scheduled during `COMPUTING` is dropped**, so the edit that
  triggered it may never be retrimmed.
- 🟡 **Shutdown cannot interrupt a worker thread** already inside a compute.
