# ADR 0005 — CAD runs in a spawned worker process because OCCT is not thread-safe

- **Status:** Accepted — in force, but **inconsistently applied**
- **Decided:** 2026-04-11 (commit `b8dd07ae`)
- **Deciders:** Marc Szymanski (maintainer)
- **Confidence:** 🟢 CONFIRMED (commit body states the root-cause investigation)

## Context

The REST CAD end-to-end test hung indefinitely. A `faulthandler` dump showed
OCCT's `.clean()` stuck in a **native loop inside the worker thread** of
`cad_service`'s `ThreadPoolExecutor`, while the identical pipeline ran from the
main thread in under three minutes. Root cause, as recorded in the commit: **OCCT
(CadQuery's C++ backend) is not thread-safe** — BRepCheck messaging, memory pools
and interrupt handlers share global state that blocks when called from a worker
thread. The same `.intersect().clean()` call takes ~100 ms on the main thread and
never returns in a worker thread.

## Decision

**Run every CAD task in its own Python interpreter, with its own main thread and
its own fresh OCCT state.**

- `ThreadPoolExecutor(max_workers=4)` → `ProcessPoolExecutor(max_workers=4)`.
- **`multiprocessing.get_context("spawn")`**, not `fork` — `fork` would fork an
  interpreter with OCCT already loaded, which is unsafe.
- A **top-level worker function** (`_run_construction_worker`) so it is picklable
  through the pool's `submit` API.
- **Everything crossing the process boundary must be picklable.** Topology objects
  hold `cq.Vector` / OCCT `gp_Vec` instances that cannot cross, so the parent
  converts `WingModel → AsbWingSchema`, ships it pickled, and the worker rebuilds
  with `asb_wing_schema_to_wing_config(schema, scale=1000.0)`.
- The executor is **lazily created** (`_get_executor`) and **explicitly torn down**
  (`shutdown_executor`) from the FastAPI lifespan shutdown hook and the test
  fixture, so workers never leak or outlive the server.
- `future.add_done_callback` writes results into the parent's in-memory `tasks`
  dict; a broken pool or worker crash is reported as task `FAILURE`.

The same reasoning was later applied to operating-point generation for a different
reason — **CasADi/IPOPT does not release the GIL**: a bounded
`ProcessPoolExecutor` (spawn, `max_workers = max(1, min(4, cpu − 1))`) reached
≈ 2.9× where a thread pool benchmarked at 0.35–0.89× (gh-867, `4cf2a672`).

## Consequences

- The hang is gone; process isolation also contains OCCT crashes; the pickle
  boundary forced a clean serialisable seam (`AsbWingSchema`), reused by the
  tessellation worker.
- **Spawn cost:** every task pays a fresh interpreter start plus the CadQuery
  import.
- 🟡 The task registry is **parent-process, in-memory only** — accepted as
  documented architecture by
  [ADR 0024](0024-single-user-desktop-operating-model.md).
- 🔴 **The decision is not applied consistently.** `construction_plan_service`
  executes plans on the **request thread** (`execute_plan`) or a
  `threading.Thread` (`execute_plan_streaming`) *inside* the FastAPI process,
  calling the same OCCT stack. Either the isolation is unnecessary or plan
  execution is exposed to the documented hang; unresolved.
- 🔴 Three process-global hazards on that path: the streaming executor arms a
  process-global display callback and `DISPLAY_CONSTRUCTION_STEP` with no lock, so
  concurrent streams cross-deliver shape events; `AbstractShapeCreator.create_shape`
  mutates the **root logger level** process-wide; and `./tmp/exports` is shared —
  the export worker zips *everything* then unlinks *every* file, while
  `check_task_available` serialises only **per aeroplane**, so concurrent exports
  for different aeroplanes destroy each other's files. The last is `Q-CG-2`, an
  open defect requiring a per-task directory.

## Related

[ADR 0001](0001-millimetres-in-cad-metres-in-db-and-aerosandbox.md) ·
[ADR 0002](0002-cad-designer-is-frozen-new-creators-only.md) ·
[ADR 0017](0017-optional-heavy-dependencies-probed-at-import.md) ·
[ADR 0024](0024-single-user-desktop-operating-model.md) · domain rule BR-67 ·
[`../questions.md`](../questions.md) §Q-CG-2.
Evidence: commits `b8dd07ae`, `4cf2a672` (gh-867);
`app/services/cad_service.py:7-20, 62-95, 303-342`;
`app/services/construction_plan_service.py:616-885` (the contradicting path).
