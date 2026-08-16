# retrim-invalidation — Implementation Tasks

> Executable sequence to re-implement this use case from the legacy behaviour.
> Every task cites the legacy file, a definition of done, and a confidence
> marker. Parent module tasks: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] `operating_points` with a `status` column defaulting to `NOT_TRIMMED` and
      a `warnings` JSON list.
- [ ] `trim_with_aerobuildup`
      ([`../operating-point-solve/tasks.md`](../operating-point-solve/tasks.md)
      T-07).
- [ ] A domain event bus with failure isolation (BR-84) and an in-memory
      debounced job tracker (`platform-core`).
- [ ] `SessionLocal` available outside the request scope.
- [ ] TED roles readable from the aeroplane schema (`wing-design`).
- [ ] `aircraft_computation_config.debounce_seconds` (default 2.0).

## Tasks

- [ ] **T-01 — The status enum and its default.**
  `NOT_TRIMMED | COMPUTING | TRIMMED | LIMIT_REACHED | DIRTY | INVALID`,
  default `NOT_TRIMMED`.
  - Legacy origin: `app/models/analysismodels.py:20`
  - Definition of done: a freshly inserted row is `NOT_TRIMMED`; every value in
    the state diagram is representable.
  - Confidence: 🟢

- [ ] **T-02 — `mark_ops_dirty`.**

  ```sql
  UPDATE operating_points SET status = 'DIRTY'
   WHERE aircraft_id = :id AND status NOT IN ('DIRTY', 'COMPUTING')
  ```

  - Legacy origin: `app/services/invalidation_service.py:26-36`
  - Definition of done: it is a **single** bulk statement (not a row loop); a
    `COMPUTING` row is untouched; an already-`DIRTY` row is not rewritten;
    `INVALID` and `LIMIT_REACHED` rows **are** re-dirtied.
  - Confidence: 🟢

- [ ] **T-03 — Geometry listeners, registered once.**
  `after_insert`, `after_update`, `after_delete` on `WingModel`,
  `WingXSecModel`, `FuselageModel`. Each: mark its own dependent tables dirty
  (`stability_results`, `avl_geometry_files`), call `mark_ops_dirty`, publish
  `GeometryChanged`.
  - Legacy origin: `app/models/stability_events.py`,
    `app/models/avl_geometry_events.py`
  - Definition of done: one geometry write publishes `GeometryChanged`
    **exactly once**.
  - 🟡 **Factor the shared listener out so a geometry write publishes `GeometryChanged` once** (`Q-AA-4`, derived; ADR 0022 applied to invalidation paths). The legacy attaches the same three models in
    **two** modules, doubling every event and every `mark_ops_dirty`. Register in
    one owning module; the AVL side subscribes to `GeometryChanged` instead of
    re-attaching its own listeners.
  - Confidence: 🟢

- [ ] **T-04 — Assumption publishers with effective-value gating.**
  `update_assumption` publishes `AssumptionChanged` and marks OPs dirty for
  `{mass, cg_x}` **only** when `active_source == "ESTIMATE"`. `switch_source`
  always publishes and additionally schedules a recompute for every parameter
  **except `cg_x`**.
  - Legacy origin: `app/services/design_assumptions_service.py` (BR-27)
  - Definition of done: editing an estimate while `CALCULATED` is active fires
    nothing; switching sources always fires.
  - Confidence: 🟢

- [ ] **T-05 — Event routing.**

  ```
  GeometryChanged   → schedule_retrim  AND  schedule_recompute_assumptions
  AssumptionChanged → schedule_retrim                if param ∈ {mass, cg_x}
                    → schedule_recompute_assumptions if param ∈ {target_static_margin, mass}
  ```

  - Legacy origin: `app/services/invalidation_service.py`
    (`_OP_AFFECTING_PARAMS`, `_RECOMPUTE_TRIGGERING_PARAMS`)
  - Definition of done: writing `cg_x` schedules **no** recompute (the loop
    guard, BR-83); writing `cd0` or `cl_max` likewise; writing `mass` schedules
    both jobs.
  - Confidence: 🟢

- [ ] **T-06 — Handlers schedule, never mark.**
  - Legacy origin: same (BR-82)
  - Definition of done: no event handler calls `mark_ops_dirty`; the marking is
    always done by the publisher, in the same transaction as the write that
    caused it.
  - 🟡 **Deviation recommended:** the legacy handler logs "OPs marked DIRTY"
    although it did not do the marking. Fix the message, or make the pairing
    explicit (e.g. a helper that does both and is the only supported way to
    publish these two events).
  - Confidence: 🟢

- [ ] **T-07 — Debounced scheduling.**
  Coalesce repeated schedule calls for the same aeroplane within
  `debounce_seconds` (default 2.0) into one run.
  - Legacy origin: `app/core/background_jobs.py`,
    `app/models/computation_config.py:8-16`
  - Definition of done: ten edits inside the window run the job once; the
    registry is in memory and is not expected to survive a restart.
  - Confidence: 🟢

- [ ] **T-08 — `retrim_dirty_ops` — session ownership and the pitch lookup.**
  Open a dedicated `SessionLocal`; find the first TED whose
  `role ∈ _PITCH_ROLES = {elevator, stabilator, elevon, ruddervator}`; if none
  exists, log a warning and return.
  - Legacy origin: `app/services/retrim_service.py:53-158`
  - Definition of done: the job commits independently of any request; a
    request-side rollback cannot undo a completed retrim.
  - 🟢 **Decided (`Q-WD-1`):** obtain the name through the mixing resolver. Previously `_find_pitch_control_name` returned the raw
    DB TED name; it works only because the trim service re-resolves display and
    role names. Return the **gh-772 mixing name** for the surface's primary
    (pitch) axis instead.
  - 🟡 **The absorbing `DIRTY` state is removed** — a state indistinguishable from "still working" in the UI is the undeclared degradation `P-WARN-0` forbids. With no pitch control the legacy leaves every OP
    `DIRTY` forever with only a log line. Emit a `NO_PITCH_CONTROL` warning on
    each row (or a distinct status) so the condition is visible in the API.
  - Confidence: 🟢 for the structure, 🔴 for both deviations

- [ ] **T-09 — The per-row claim-and-solve loop.**

  ```
  for op in SELECT … WHERE aircraft_id = :id AND status = 'DIRTY':
      op.status = 'COMPUTING' ; commit            # the claim
      solve → TRIMMED | LIMIT_REACHED
      ValidationDomainError / Pydantic error → INVALID   (terminal for retry)
      any other exception                     → NOT_TRIMMED (retryable)
      commit
  ```

  - Legacy origin: `app/services/retrim_service.py:53-158`
  - Definition of done: the `COMPUTING` write is committed **before** the solve
    starts; a corrupt row ends `INVALID` and the next cycle's
    `WHERE status = 'DIRTY'` skips it; a transient error ends `NOT_TRIMMED`.
  - Confidence: 🟢

- [ ] **T-10 — Write the trim result back.**
  On convergence write the deflection into `controls` / `control_deflections`
  and set `TRIMMED`; on a bound hit set `LIMIT_REACHED`.
  - Legacy origin: same
  - Definition of done: a re-read of the row reproduces the trim; a
    `LIMIT_REACHED` row is never reported as trimmed.
  - Confidence: 🟢

- [ ] **T-11 — Post-retrim stability refresh.**
  When at least one OP trimmed, recompute the stability summary from the
  **first** trimmed operating point.
  - Legacy origin: `app/services/retrim_service.py` +
    `app/services/stability_service.py`
  - Definition of done: after a successful retrim the cached stability row is
    `CURRENT` again; with zero successful trims nothing is recomputed.
  - Confidence: 🟢

- [ ] **T-12 — Subscriber isolation.**
  A raising handler must not roll back or fail the publishing write.
  - Legacy origin: `app/core/events.py` (BR-84)
  - Definition of done: a handler that raises leaves the wing update committed
    and logs the error.
  - Confidence: 🟢

- [ ] **T-13 — A reaper for orphaned `COMPUTING` rows.**
  A row left in `COMPUTING` by a process restart is invisible to both
  `mark_ops_dirty` (which excludes it) and the retrim selection (which looks for
  `DIRTY`), so it is stuck permanently.
  - Legacy origin: **absent** — this is a gap, not a reproduction
  - Definition of done: a `COMPUTING` row older than a configured threshold is
    returned to `DIRTY` on the next retrim pass, with a logged reason.
  - Confidence: 🟡 (new behaviour; the legacy has no recovery path)

## Test Tasks

- [ ] **TT-01 — Marking.** Three TRIMMED rows → all `DIRTY`; a `COMPUTING` row is
      untouched; an already-`DIRTY` row is not rewritten (assert the affected row
      count).
- [ ] **TT-02 — `INVALID` and `LIMIT_REACHED` are re-dirtied** by a new
      invalidation.
- [ ] **TT-03 — Single publication.** One wing update publishes
      `GeometryChanged` exactly once (guards the T-03 deviation).
- [ ] **TT-04 — Effective-value gating.** Estimate edit under `CALCULATED` →
      no event, no dirty rows; `switch_source` → event.
- [ ] **TT-05 — Loop guard.** `AssumptionChanged(cg_x)` schedules no recompute;
      `AssumptionChanged(mass)` schedules retrim **and** recompute;
      `AssumptionChanged(prop_efficiency)` schedules neither.
- [ ] **TT-06 — Debounce.** Ten schedule calls in the window → one run.
- [ ] **TT-07 — Session ownership.** A retrim commit survives a simulated
      request-scope rollback.
- [ ] **TT-08 — Claim.** The row is observed in `COMPUTING` before the solver is
      called (assert ordering with a mock).
- [ ] **TT-09 — `INVALID` is terminal.** A Pydantic error yields `INVALID`; a
      second retrim pass does not touch it.
- [ ] **TT-10 — Transient failure is retryable.** Any other exception yields
      `NOT_TRIMMED` and is picked up after the next invalidation.
- [ ] **TT-11 — Bound hit.** A trim converging onto a bound yields
      `LIMIT_REACHED`, not `TRIMMED`.
- [ ] **TT-12 — No pitch control.** Rows stay `DIRTY`, a warning is logged, **and**
      (after the T-08 deviation) each row carries a `NO_PITCH_CONTROL` warning.
- [ ] **TT-13 — Stability refresh** happens only when at least one OP trimmed.
- [ ] **TT-14 — Subscriber isolation.** A raising handler leaves the write
      committed.
- [ ] **TT-15 — #955 regression.** On a V-tail aircraft the background retrim
      resolves the pitch control by its **mixing name** and trims successfully.
- [ ] **TT-16 — Orphan reaper (T-13).** A `COMPUTING` row older than the
      threshold returns to `DIRTY`.
- [ ] **TT-17 — Fast-tier coverage.** All of the above run **without**
      AeroSandbox by stubbing `trim_with_aerobuildup` (ADR 0015).

## Suggested Order

1. **T-01, T-02** — the status column and the marking statement are the
   foundation; every other task observes them.
2. **T-03, T-04** — the publishers, so there is something to react to. T-03
   carries the duplicate-registration deviation and should be settled early,
   because every later test asserts an event count.
3. **T-05, T-06, T-07** — routing, the marking/publishing separation, and the
   debounce.
4. **T-08 → T-10** — the retrim job itself. T-08's two deviations (#955 naming,
   the absorbing state) must be decided before T-09 freezes the loop's exit
   conditions.
5. **T-11** after the loop works.
6. **T-12** any time (it is an event-bus property).
7. **T-13** last — it is new behaviour and needs the loop's semantics settled.

Blocking edges: T-02 ⇠ T-01 · T-03, T-04 ⇠ T-02 · T-05 ⇠ T-03, T-04 ·
T-09 ⇠ T-08 · T-10, T-11 ⇠ T-09 · T-13 ⇠ T-09.

## Pending Gaps

- **The absorbing `DIRTY` state (T-08).** With no pitch-role TED nothing will
  ever happen, and only a log line records it. Should this be a distinct status,
  a row-level warning, or a validation at operating-point-generation time that
  refuses to create OPs for an aircraft that cannot be trimmed?
- **Duplicate listener registration (T-03).** Two modules attach the same three
  models. Which one owns them, and should the other subscribe to
  `GeometryChanged` instead?
- **`_find_pitch_control_name` returns the DB name (T-08, bug #955).** It works
  only by accident of re-resolution downstream. Fix the name — and decide
  whether the retrim should trim *every* pitch-capable surface or only the first
  one it finds.
- **Orphaned `COMPUTING` rows (T-13).** No reaper exists. A restart mid-solve
  leaves a row permanently invisible to both the marker and the retrim
  selection. What is the right staleness threshold?
- **Only pitch is re-trimmed.** Turn operating points carry roll/yaw deflections
  that are never refreshed in the background, so a lateral trim silently ages
  after a geometry change.
- **Warnings are never cleared.** Should a successful retrim prune the warning
  list, or is the accumulation the intended audit trail? Today a `TRIMMED` row
  can still carry a `NOT_TRIMMED` warning.
- **The claim is optimistic.** No row-level lock; two schedulers racing on the
  same aircraft could both read `DIRTY`. Is a `SELECT … FOR UPDATE` (or a
  conditional `UPDATE … WHERE status = 'DIRTY'` returning the affected count)
  warranted, given SQLite's WAL mode and a 30 s busy timeout (BR-80)?
