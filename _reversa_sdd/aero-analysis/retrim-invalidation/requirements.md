# retrim-invalidation

> Use-case specification, nested under the module
> [`aero-analysis`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: aero-analysis
> (Operating points — status machine and invalidation),
> `_reversa_sdd/state-machines.md` §1 and §7, `_reversa_sdd/domain.md`
> BR-82/BR-83/BR-84.

## Overview

`retrim-invalidation` keeps stored trim state honest. When the geometry or a
mass/CG assumption changes, every affected operating point is marked `DIRTY`
and a debounced background job re-trims it. It is the only loop in the system
that repairs persisted numbers without a user request — and the only one whose
failure mode is *silence*: an operating point that never leaves `DIRTY` looks
merely stale, not broken. 🟢

## Responsibilities

- Mark every affected operating point `DIRTY` when geometry or a relevant
  assumption changes. 🟢
- Publish `GeometryChanged` / `AssumptionChanged` so the debounced job scheduler
  can pick the work up. 🟢
- Route each event to the right jobs, excluding the parameters that are the
  jobs' own outputs. 🟢
- Re-trim DIRTY operating points in the background, in their **own** database
  session. 🟢
- Move each row to the correct terminal state — `TRIMMED`, `LIMIT_REACHED`,
  `INVALID` (terminal for retry) or `NOT_TRIMMED` (retryable). 🟢
- Recompute stability from the first trimmed operating point when at least one
  trim succeeded. 🟢

**Explicitly NOT this use case's responsibility:** the trim algorithm itself
(→ [`../operating-point-solve/`](../operating-point-solve/requirements.md)),
generating the operating-point set
(→ [`../../mission-and-sizing/operating-point-sweep/`](../../mission-and-sizing/operating-point-sweep/requirements.md)),
the recompute pipeline it schedules alongside
(→ [`../aero-context-single-source/`](../aero-context-single-source/requirements.md)),
and the job-tracker plumbing itself (→ `platform-core`).

## Business Rules

- **BR-AA18 — The operating point is the only entity with a persisted,
  multi-valued status.** 🟢
  `NOT_TRIMMED | COMPUTING | TRIMMED | LIMIT_REACHED | DIRTY | INVALID`
  (`app/models/analysismodels.py:20`, default `NOT_TRIMMED`).

  | From | To | Trigger | Guard |
  |---|---|---|---|
  | — | `NOT_TRIMMED` | row inserted by `_persist_point_set` | column default |
  | `NOT_TRIMMED` | `TRIMMED` | two-stage trim | `trim_score < 0.35` |
  | `NOT_TRIMMED` | `LIMIT_REACHED` | trim solve | `\|α\| > max_alpha_deg`, `\|β\| > max_beta_deg`, or `V < V_s1·√n` in a turn (`STALL_IN_TURN`) |
  | any except `DIRTY`/`COMPUTING` | `DIRTY` | `mark_ops_dirty(session, aeroplane_id)` | bulk `UPDATE` |
  | `DIRTY` | `COMPUTING` | `retrim_dirty_ops` claims the row | runs in its own `SessionLocal` |
  | `COMPUTING` | `TRIMMED` | `trim_with_aerobuildup(Cm = 0)` converged | writes the deflection into `control_deflections` |
  | `COMPUTING` | `LIMIT_REACHED` | the solver hit a bound | |
  | `COMPUTING` | `INVALID` | `ValidationDomainError` / Pydantic error | **terminal for retry** |
  | `COMPUTING` | `NOT_TRIMMED` | any other exception | deliberately retryable |
  | `DIRTY` | `DIRTY` | no TED with a role in `_PITCH_ROLES` | **absorbing** 🟡 (removed, `P-WARN-0`) |

- **BR-RI1 — `mark_ops_dirty` never touches a row already `DIRTY` or
  `COMPUTING`.** 🟢 (`invalidation_service.py:26-36`) A bulk `UPDATE` excluding
  those two states, so a marking storm cannot interrupt a running retrim or
  re-dirty an already-dirty row.
- **BR-RI2 — `INVALID` is terminal for retry.** 🟢 "Retrying cannot fix a corrupt
  row." A `ValidationDomainError` or a Pydantic error means the stored row
  itself is unusable; only an explicit edit can rescue it. Any *other*
  exception yields `NOT_TRIMMED`, which the next cycle will retry.
- **BR-82 — Marking dirty and publishing are separate responsibilities.** 🟢/🟡
  Every publisher calls `mark_ops_dirty` **and** `event_bus.publish` by hand.
  Handlers only schedule jobs — they never mark. The pairing is a convention, not
  an enforced invariant, and the handler log line ("OPs marked DIRTY") describes
  something the handler did not do. 🟡
- **BR-RI3 — Seven publishers mark, three models trigger.** 🟢
  `WingModel`, `WingXSecModel` and `FuselageModel` via
  `after_insert/update/delete`; plus `design_assumptions_service.update` /
  `switch_source`, `mass_cg_service` (×2), `loading_scenario_service` and
  `assumption_compute_service`.
- **BR-83 — Recompute triggers exclude their own outputs.** 🟢
  `GeometryChanged` → `job_tracker.schedule_retrim` **and**
  `schedule_recompute_assumptions`.
  `AssumptionChanged` → retrim only for `_OP_AFFECTING_PARAMS = {mass, cg_x}`;
  recompute only for `_RECOMPUTE_TRIGGERING_PARAMS = {target_static_margin,
  mass}`. `cg_x`, `cd0` and `cl_max` are deliberately excluded from the
  recompute set to break the `recompute → AssumptionChanged(cg_x) → recompute`
  loop.
- **BR-27 — Events fire only when the *effective* value changes.** 🟢
  `update_assumption` publishes `AssumptionChanged` (and marks OPs dirty for
  `mass`/`cg_x`) **only** when `active_source == "ESTIMATE"` — editing an
  estimate while the calculated value is active changes nothing effective, so
  the retrim chain must not fire. `switch_source` always fires.
- **BR-RI4 — The retrim owns its transaction.** 🟢 `retrim_dirty_ops` opens its
  **own** `SessionLocal` because it runs outside a request; the `get_db()`
  boundary (BR-78) does not apply, so it owns the commit/rollback itself.
- **BR-RI5 — Retrim trims pitch only, on the first pitch-role TED.** 🟢 It finds
  the first TED whose `role ∈ _PITCH_ROLES = {elevator, stabilator, elevon,
  ruddervator}` and solves `Cm = 0` on it with AeroBuildup.
- **BR-RI6 — Stability is recomputed from the first trimmed operating point.** 🟢
  Only when at least one OP actually trimmed.
- **BR-84 — A broken subscriber can never break the publishing request.** 🟢 The
  event bus isolates handler failures from the write that triggered them.
- **BR-RI7 — Warnings accumulate and are not cleared.** 🟡 The warning vocabulary
  (`STALE_NO_POLAR`, `FLAP_DEFLECTION_CLIPPED`, `ALPHA_LIMIT_REACHED`,
  `BETA_LIMIT_REACHED`, `STALL_IN_TURN`, `NOT_TRIMMED`, `NO_CONTROL_TRIM_MVP`) is
  orthogonal to `status`; a successful retrim does not remove earlier warnings.
- 🔴 **BR-RI8 — `DIRTY` is absorbing without a pitch control.** With no
  pitch-role TED in the geometry, every OP stays `DIRTY` **forever**, recorded
  only as a log warning. To a user the aircraft looks perpetually "recomputing".
- 🔴 **BR-RI9 — The geometry listeners are registered twice.**
  `stability_events.py` and `avl_geometry_events.py` each attach
  `after_insert/update/delete` to the same three models, so every geometry write
  publishes `GeometryChanged` twice and calls `mark_ops_dirty` twice.
- 🟢 **Bug #955 is resolved structurally** (`Q-WD-1`, maintainer-answered): `control_surface_mixing` owns a resolver that trim, retrim and stability are **required** to call, and the silent ±25° fallback is removed. Keying on the raw DB TED name becomes impossible rather than merely discouraged.
  `retrim_service._find_pitch_control_name` returns the TED's raw `name`, used as
  a `trim_variable`. It works today **only** because the AeroBuildup trim service
  re-resolves display and role names; it is not the canonical gh-772 mixing name.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Mark every non-`DIRTY`/`COMPUTING` OP dirty on a geometry write | Must | Editing a wing station flips three TRIMMED OPs to `DIRTY` |
| RF-02 | Leave `COMPUTING` rows untouched while marking | Must | A running retrim is not interrupted by a concurrent edit |
| RF-03 | Publish `GeometryChanged` on wing / x-section / fuselage writes | Must | The event fires **once** per write |
| RF-04 | Publish `AssumptionChanged` only when the effective value changes | Must | Editing an estimate while `CALCULATED` is active fires nothing |
| RF-05 | Route `GeometryChanged` to both retrim and recompute | Must | Both jobs are scheduled |
| RF-06 | Route `AssumptionChanged` to retrim only for `{mass, cg_x}` | Must | Editing `prop_efficiency` schedules no retrim |
| RF-07 | Route `AssumptionChanged` to recompute only for `{target_static_margin, mass}` | Must | Writing `cg_x` schedules no recompute (loop guard) |
| RF-08 | Debounce scheduled jobs | Should | A burst of edits inside `debounce_seconds` runs one job |
| RF-09 | Re-trim DIRTY OPs in a dedicated session | Must | A request rollback cannot undo a completed retrim |
| RF-10 | Claim a row by moving it to `COMPUTING` before solving | Must | Two concurrent retrims do not both solve the same row |
| RF-11 | Trim `Cm = 0` on the first pitch-role TED with AeroBuildup | Must | The resulting deflection is written into `control_deflections` |
| RF-12 | End at `TRIMMED` or `LIMIT_REACHED` on a completed solve | Must | A bound-hit row is `LIMIT_REACHED`, not `TRIMMED` |
| RF-13 | Mark a corrupt row `INVALID` and never retry it | Must | A Pydantic error yields `INVALID`; the next cycle skips it |
| RF-14 | Revert any other failure to `NOT_TRIMMED` | Must | A transient solver error is retried on the next cycle |
| RF-15 | Recompute stability from the first trimmed OP | Should | After a successful retrim the cached stability is refreshed |
| RF-16 | Log a warning and leave OPs `DIRTY` when no pitch control exists | Must (today) | 🔴 the state is absorbing; see Gaps |
| RF-17 | Never let a subscriber failure break the triggering write | Must | A raising handler does not roll back the wing edit |
| RF-18 | Expose the job state for polling | Should | `GET …/assumptions/recompute-status` reports queued / running / idle |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Availability | The retrim runs outside the request and owns its own commit/rollback | `retrim_service.py:53-158` | 🟢 |
| Availability | A broken subscriber cannot break the publishing request | BR-84, event bus | 🟢 |
| Consistency | Marking is a single bulk `UPDATE`, excluding `DIRTY`/`COMPUTING` | `invalidation_service.py:26-36` | 🟢 |
| Consistency | `COMPUTING` acts as the claim, so a row is solved once | retrim loop | 🟡 |
| Correctness | Recompute triggers exclude the recompute's own outputs, breaking the feedback loop | `_RECOMPUTE_TRIGGERING_PARAMS` (BR-83) | 🟢 |
| Correctness | `INVALID` is terminal, because retrying cannot repair a corrupt row | retrim exception branches | 🟢 |
| Performance | Jobs are debounced (`debounce_seconds = 2.0`) so a drag-edit burst runs one pass | `aircraft_computation_config` | 🟢 |
| Durability | The job registry is **in-memory only**; a restart loses queued work, but the `DIRTY` rows survive and are picked up next time | `platform-core` background jobs | 🟡 |
| Observability | Every transition is visible in `status`; the reasons are in `warnings[]` and the log | `operating_points` | 🟡 |

## Acceptance Criteria

```gherkin
Feature: Invalidation

  Scenario: A geometry edit dirties every operating point
    Given three TRIMMED operating points
    When a wing cross-section is updated
    Then all three have status DIRTY

  Scenario: A running retrim is not disturbed
    Given one operating point in COMPUTING and two in TRIMMED
    When a geometry edit marks the aircraft dirty
    Then the COMPUTING row keeps its status
    And the two TRIMMED rows become DIRTY

  Scenario: An already dirty row is not re-marked
    Given an operating point in DIRTY
    When another geometry edit occurs
    Then no UPDATE touches that row

  Scenario: An estimate edit under an active calculation fires nothing
    Given the mass assumption with active_source CALCULATED
    When the estimate value is edited
    Then no AssumptionChanged is published
    And no operating point becomes DIRTY

  Scenario: Writing cg_x does not schedule a recompute
    Given a recompute that has just written cg_x
    When AssumptionChanged for cg_x is handled
    Then no recompute is scheduled
    # otherwise recompute -> AssumptionChanged(cg_x) -> recompute loops forever

  Scenario: A subscriber failure does not break the write
    Given a handler that raises
    When a wing is updated
    Then the wing update is committed
    And the error is logged

Feature: Background retrim

  Scenario: A dirty point is claimed and trimmed
    Given a DIRTY operating point and an elevator TED
    When retrim_dirty_ops runs
    Then the row passes through COMPUTING
    And ends at TRIMMED with a deflection in control_deflections

  Scenario: A bound hit is reported as LIMIT_REACHED
    Given a DIRTY operating point whose trim converges onto a deflection bound
    When it is retrimmed
    Then its status is LIMIT_REACHED
    And it is not reported as TRIMMED

  Scenario: A corrupt row is not retried forever
    Given a DIRTY operating point whose stored row fails Pydantic validation
    When retrim_dirty_ops processes it
    Then its status becomes INVALID
    And a warning is logged
    And the next retrim cycle does not pick it up

  Scenario: A transient failure stays retryable
    Given a DIRTY operating point whose solve raises a transient error
    When it is processed
    Then its status becomes NOT_TRIMMED
    And it is picked up again after the next invalidation

  Scenario: The retrim owns its transaction
    Given a retrim running outside any request
    When it commits a trimmed row
    Then the commit survives independently of any request lifecycle

  Scenario: Stability is refreshed after a successful retrim
    Given at least one operating point trimmed
    When the retrim finishes
    Then the stability summary is recomputed from the first trimmed point

  Scenario: No pitch control leaves the points dirty
    Given an aircraft with no TED whose role is elevator, stabilator, elevon or ruddervator
    When retrim_dirty_ops runs
    Then every operating point stays DIRTY
    And a warning is logged
    # 🟡 **The absorbing `DIRTY` state is removed** — a state indistinguishable from "still working" in the UI is the undeclared degradation `P-WARN-0` forbids.
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Dirty marking on geometry + `{mass, cg_x}` (RF-01, RF-06) | Must | Without it every stored trim silently describes an older aircraft |
| Excluding `DIRTY`/`COMPUTING` from marking (RF-02) | Must | Prevents interrupting an in-flight retrim |
| The loop guard on `cg_x` (RF-07) | Must | Otherwise the recompute retriggers itself indefinitely |
| Effective-value gating (RF-04) | Must | BR-27; otherwise every estimate edit triggers a full solver pass |
| Dedicated session (RF-09) | Must | The job runs outside the `get_db()` boundary |
| Claim via `COMPUTING` (RF-10) | Must | The only concurrency control on the retrim |
| Correct terminal states (RF-12…RF-14) | Must | `INVALID` vs `NOT_TRIMMED` decides whether work repeats forever |
| Subscriber isolation (RF-17) | Must | BR-84; a background concern must never fail a user write |
| Debounce (RF-08) | Should | A performance property, not a correctness one |
| Stability refresh (RF-15) | Should | A convenience — the summary can also be requested explicitly |
| Job-state polling (RF-18) | Should | UI affordance |
| Making the no-pitch-control case explicit | **Must (open)** | 🔴 today it is an absorbing `DIRTY` with only a log line |
| Registering the listeners once | **Must (open)** | 🔴 duplicate registration doubles every event |
| Using the gh-772 mixing name for the pitch control | **Must (open)** | 🔴 bug #955; works today only by accident of re-resolution |
| Clearing warnings on a successful retrim | Could | 🟡 the accumulation may be the intended audit trail |
| Persisting the job queue | Won't | In-memory by design; `DIRTY` rows are the durable queue |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/invalidation_service.py` | `mark_ops_dirty` (`:26-36`), `_OP_AFFECTING_PARAMS`, `_RECOMPUTE_TRIGGERING_PARAMS`, event handlers | 🟢 |
| `app/services/retrim_service.py` | `retrim_dirty_ops` (`:53-158`), `_find_pitch_control_name`, `_PITCH_ROLES` | 🟢 / 🔴 (#955) |
| `app/models/stability_events.py` | `after_insert/update/delete` on `WingModel`, `WingXSecModel`, `FuselageModel` | 🟢 |
| `app/models/avl_geometry_events.py` | the **duplicate** registration of the same three models | 🔴 |
| `app/models/analysismodels.py` | `OperatingPointModel.status`, `warnings` | 🟢 |
| `app/core/events.py` | `GeometryChanged`, `AssumptionChanged`, the event bus | 🟢 |
| `app/core/background_jobs.py` | `job_tracker.schedule_retrim`, `schedule_recompute_assumptions` (in-memory) | 🟢 |
| `app/services/design_assumptions_service.py` | `update_assumption`, `switch_source` (BR-27 gating) | 🟢 |
| `app/services/stability_service.py` | the post-retrim stability refresh | 🟢 |
