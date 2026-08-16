# design-assumptions

> Use-case specification, nested under the module
> [`mission-and-sizing`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: mission-and-sizing
> (R1–R3), `_reversa_sdd/data-dictionary.md` §`design_assumptions` /
> §`aircraft_computation_config`, `_reversa_sdd/domain.md` BR-24…BR-28, BR-83,
> `_reversa_sdd/state-machines.md` §5, ADR 0010, ADR 0011.

## Overview

`design-assumptions` is the **numeric substrate** of the whole application:
fifteen named parameters, each carrying a user **estimate** and — where physics
can supply one — a **calculated** value, plus a selector saying which of the two
is currently effective. Every other module reads its numbers through this layer,
so its two hardest jobs are not arithmetic: deciding **when a change is
effective** (and therefore when the expensive downstream chain may fire), and
deciding **which parameters physics is allowed to touch at all**. 🟢

It also owns `aircraft_computation_config` — the per-aircraft sweep tuning that
the recompute pipeline reads. 🟢

## Responsibilities

- Seed the fifteen catalogued parameters and the computation config,
  idempotently and unconditionally. 🟢
- Compute `effective_value`, `divergence_pct` and `divergence_level` on every
  read. 🟢
- Accept an estimate edit and publish `AssumptionChanged` **only when the
  effective value actually changed**. 🟢
- Accept a source switch, refusing it for the seven design choices and for a
  parameter with no calculated value. 🟢
- Accept a calculated value from the compute/aggregation services and
  auto-switch the source **once**. 🟢
- Break the `recompute → AssumptionChanged(cg_x) → recompute` loop. 🟢
- Expose the cached computation context read-only and expose the recompute job
  state. 🟢
- Read and partially update the per-aircraft computation config. 🟢

**Explicitly NOT this use case's responsibility:** producing the calculated
values (→ `aero-analysis`, `assumption_compute_service`), aggregating mass from
the component tree (→ `mass-and-balance`), writing the preset estimates
(→ [`../mission-objectives-presets/`](../mission-objectives-presets/requirements.md)),
and the retrim that `AssumptionChanged` triggers (→ `aero-analysis`).

## Business Rules

> Global ids (`BR-*`) are inherited verbatim from
> [`../../domain.md`](../../domain.md); `BR-MS*` from
> [`../requirements.md`](../requirements.md). `BR-MS30`…`BR-MS33` are new,
> discovered while writing this specification.

- **BR-24 — Every parameter has an estimate and a calculation (ADR 0010).** 🟢

  ```
  effective_value = calculated_value  if active_source == "CALCULATED"
                                      and calculated_value is not None
                    else estimate_value
  divergence_pct  = round(|estimate − calculated| / |calculated| · 100, 1)
  divergence_level: < 5 none · < 15 info · ≤ 30 warning · else alert
  ```

- **BR-MS30 — Divergence is undefined, not zero, when there is nothing to
  compare against.** 🟢 `compute_divergence_pct` returns `None` when
  `calculated is None` **or** `calculated == 0`; `divergence_level(None)` is
  `"none"`. The rounding to **one decimal** is part of the contract — clients
  display the stored value.
  🔴 A parameter whose calculated value is legitimately `0.0` (e.g.
  `t_static_N` for a glider, `power_to_weight` for a sailplane preset) therefore
  never reports a divergence, however far the estimate is from it.
- **BR-25 — Auto-switch happens once.** 🟢
  `update_calculated_value(..., auto_switch_source=True)` flips `active_source`
  to `CALCULATED` only when **all four** hold: the caller asked for it, the row
  has `calculated_value IS NULL`, `active_source == "ESTIMATE"`, and the
  parameter is not a design choice. Afterwards the user's manual choice sticks
  forever.
- **BR-26 — Design choices can never be calculated.** 🟢 The seven
  `DESIGN_CHOICE_PARAMS` — `target_static_margin`, `g_limit`,
  `battery_capacity_wh`, `battery_specific_energy_wh_per_kg`,
  `propulsion_eta_motor`, `propulsion_eta_esc`, `motor_continuous_power_w` —
  never auto-switch and are refused with **422** on an explicit switch.
  🟡 Nothing stops `update_calculated_value` from *writing* a
  `calculated_value` onto a design choice; only the switch is guarded, so a
  design choice could display a divergence it can never act on.
- **BR-27 — Events fire only when the *effective* value changes.** 🟢

  | Action | Publishes `AssumptionChanged` | Marks OPs `DIRTY` | Schedules a recompute |
  |---|---|---|---|
  | `update_assumption` while `active_source == ESTIMATE` | yes | for `{mass, cg_x}` | via the event router, for `_RECOMPUTE_TRIGGERING_PARAMS` |
  | `update_assumption` while `active_source == CALCULATED` | **no** | no | no |
  | `switch_source` (either direction) | **always** | for `{mass, cg_x}` | **directly**, for every parameter except `cg_x` |
  | `update_calculated_value` | **no** | no | no |

  Editing an estimate while the calculated value is active changes nothing
  effective, so the retrim chain must not fire.
  🟡 `switch_source` calls `job_tracker.schedule_recompute_assumptions`
  **directly**, in addition to publishing the event — a second, non-event path
  into the same job.
- **BR-83 — Recompute triggers exclude their own outputs.** 🟢
  `_RECOMPUTE_TRIGGERING_PARAMS = {target_static_margin, mass}`. `cg_x`, `cd0`
  and `cl_max` are excluded because they are what the recompute *writes* —
  including them would loop. The `switch_source` shortcut applies the same rule
  by excluding `cg_x` explicitly.
- **BR-28 — CG is a top-down design target (gh-465, ADR 0011).** 🟢 `cg_x` is
  *CG_aero*, `x_np − SM·MAC`, written by `assumption_compute_service`. The
  aggregated CG from mass items is **never** written back into `cg_x`.
- **BR-MS1 — Seeding is idempotent and unconditional.** 🟢 `seed_defaults`
  inserts only the missing parameter rows and creates the computation-config row
  only when absent; `recompute_assumptions` calls it on every run because wings
  can be created before the user ever opens the Assumptions tab.
- **BR-MS2 — Fifteen parameters, seven of them design choices.** 🟢 Full table
  in [`../contracts.md`](../contracts.md) §A.
  🟡 `min_static_margin` / `max_static_margin` are **read** by
  `stability_service` but are not in `VALID_PARAMETERS`, have no default, and are
  never seeded — so the 5 % / 25 % CG-range bounds they gate are unreachable
  configuration.
- **BR-MS31 — The parameter name is validated by the transport, not the
  service.** 🟢 `_PARAM_NAME_PATTERN` is assembled at import time from
  `PARAMETER_DEFAULTS.keys()` and applied as a **path regex**, so an unknown
  name is a FastAPI **422 path-validation** error and never reaches the service.
  Adding a parameter to `PARAMETER_DEFAULTS` therefore widens the URL space
  automatically.
- **BR-MS32 — Reading the computation config creates it.** 🟢 Both
  `GET` and `PUT` on `…/computation-config` insert a row from
  `COMPUTATION_CONFIG_DEFAULTS` when none exists. The `PUT` merges with
  `model_dump(exclude_none=True)`, so an omitted or `null` field keeps its
  current value.
  🔴 There is no cross-field validation: `coarse_alpha_min_deg = 30` together
  with `coarse_alpha_max_deg = 10` is accepted and produces an empty sweep.
- **BR-MS33 — The recompute job is observable, and "accepted" is not
  "started".** 🟢 `GET …/assumptions/recompute-status` and
  `POST …/recompute` return the identical envelope
  `{status, started_at, finished_at, error}` read from `job_tracker`;
  with no job row `status` is `"idle"` and the three others are `null`.
  🟡 The POST answers **202 Accepted** even when no event loop was available to
  schedule the task — it returns `status: "idle"` and the client must notice.
- 🔴 **BR-MS-open — Two readers of the same effective value.**
  `design_assumptions_service.get_effective_assumption(db, aeroplane_id: int,
  param)` returns `float | None` and falls back to `PARAMETER_DEFAULTS` on a
  missing row; `mass_cg_service.get_effective_assumption_value(db,
  aeroplane_uuid, param)` returns `float` and **raises `NotFoundError`** on a
  missing row. Different key type, different return type, different missing-row
  policy. `flight_envelope_service` uses the second and catches the exception to
  restore the first's behaviour.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Seed the fifteen catalogued parameters idempotently | Must | A second `POST …/assumptions` leaves 15 rows |
| RF-02 | Seed the computation config in the same call | Must | One `aircraft_computation_config` row exists after seeding |
| RF-03 | Return `effective_value` per the active source | Must | `CALCULATED` + non-null ⇒ the calculated value; otherwise the estimate |
| RF-04 | Return `divergence_pct` rounded to one decimal, `None` when the calculated value is null or zero | Must | `est 1.5 / calc 1.8` ⇒ `16.7`; `calc 0` ⇒ `null` |
| RF-05 | Map divergence to `none` / `info` / `warning` / `alert` | Must | `12 %` ⇒ `info`; `31 %` ⇒ `alert` |
| RF-06 | Count `warning` **and** `alert` rows into `warnings_count` | Should | Three `warning` + one `alert` ⇒ `4` |
| RF-07 | Reject NaN/Inf as an estimate | Must | `allow_inf_nan=False` on `AssumptionWrite` ⇒ 422 |
| RF-08 | Reject an unknown parameter name at the path level | Must | `PUT …/assumptions/thrust` ⇒ 422, service not entered |
| RF-09 | Publish `AssumptionChanged` only when the effective value changes | Must | Editing an estimate under an active `CALCULATED` publishes nothing |
| RF-10 | Mark operating points `DIRTY` for `mass` and `cg_x` only | Must | Editing `cl_max` dirties no OP |
| RF-11 | Always publish on `switch_source` | Must | Both directions publish |
| RF-12 | Schedule a recompute on `switch_source` for every parameter except `cg_x` | Must | Switching `cg_x` schedules none |
| RF-13 | Refuse `CALCULATED` for a design-choice parameter | Must | `PATCH …/g_limit/source {CALCULATED}` ⇒ 422 with the design-choice message |
| RF-14 | Refuse `CALCULATED` when no calculated value exists | Must | ⇒ 422 *"No calculated value available for '<name>'"* |
| RF-15 | Auto-switch to `CALCULATED` on the **first** calculated value only | Must | A second calculated value does not override a manual switch back |
| RF-16 | Never auto-switch a design choice | Must | `g_limit` stays `ESTIMATE` after any `update_calculated_value` |
| RF-17 | Recompute divergence on every calculated-value write | Must | The row's `divergence_pct` reflects the new pair |
| RF-18 | Expose the cached computation context read-only | Must | `GET …/computation-context` returns the JSON or `null`, never a stub |
| RF-19 | Expose the recompute job state | Should | No job ⇒ `{"status":"idle", nulls}` |
| RF-20 | Accept a forced recompute with 202 | Should | Returns the job envelope even when scheduling failed |
| RF-21 | Create the computation config on read | Should | `GET …/computation-config` on a fresh aircraft returns the defaults |
| RF-22 | Merge a partial computation-config update | Should | Omitted fields keep their current value |
| RF-23 | Enforce the per-field bounds of the computation config | Must | `fine_velocity_count = 1` ⇒ 422; `debounce_seconds = 60` ⇒ 422 |
| RF-24 | Report `unit` and `is_design_choice` on every read | Should | `mass` ⇒ `"kg"`, `false`; `g_limit` ⇒ `"g"`, `true` |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Correctness | The effective-value rule exists in exactly one place per reader, and downstream code never branches on `active_source` | `_assumption_to_read`, `get_effective_assumption` | 🟢 |
| Correctness | The event gate prevents a solver storm from a no-op edit | `update_assumption` (BR-27) | 🟢 |
| Correctness | `cg_x` is excluded from recompute triggers to break a self-feeding loop | `switch_source`, `_RECOMPUTE_TRIGGERING_PARAMS` (BR-83) | 🟢 |
| Correctness | NaN/Inf can never enter an estimate | `Field(allow_inf_nan=False)` | 🟢 |
| Robustness | Seeding is safe to call on every recompute | `seed_defaults` (BR-MS1) | 🟢 |
| Robustness | A missing assumption row degrades to the catalogue default rather than failing | `get_effective_assumption` | 🟢 |
| Performance | The recompute is debounced (`debounce_seconds = 2.0`) so a slider drag enqueues one job | `aircraft_computation_config` | 🟢 |
| Observability | The recompute job exposes `status`, `started_at`, `finished_at`, `error` so the UI can show "Recomputing…" regardless of which event triggered it | `get_recompute_status` | 🟢 |
| Observability | `calculated_source` records **which** service produced the number | `design_assumptions` column | 🟢 |
| Auditability | `divergence_pct` is persisted, so a stale estimate is visible without recomputation | same | 🟢 |
| Traceability | `updated_at` carries `onupdate` | model definition | 🟢 |
| Interoperability | The URL space is derived from the catalogue, so transport and schema cannot drift | `_PARAM_NAME_PATTERN` (BR-MS31) | 🟢 |

## Acceptance Criteria

```gherkin
Feature: The estimate/calculated duality

  Scenario: The effective value follows the active source
    Given an assumption with estimate 1.5 and calculated 1.8
    When active_source is CALCULATED
    Then the effective value is 1.8
    And divergence_pct is 16.7
    And divergence_level is "warning"

  Scenario: The effective value falls back to the estimate
    Given an assumption with estimate 1.5 and no calculated value
    Then the effective value is 1.5
    And divergence_pct is null
    And divergence_level is "none"

  Scenario: A zero calculated value hides the divergence
    Given an assumption with estimate 18.0 and calculated 0.0
    Then divergence_pct is null
    # 🔴 the estimate is infinitely far from the calculation and nothing says so

Feature: Seeding

  Scenario: Seeding is idempotent
    Given an aeroplane with no assumptions
    When I seed twice
    Then there are exactly 15 assumption rows
    And exactly one aircraft_computation_config row

  Scenario: Seeding preserves user edits
    Given a seeded aeroplane whose mass estimate is 2.4
    When seed_defaults runs again
    Then the mass estimate is still 2.4

Feature: Event gating

  Scenario: An estimate edit under an active calculation is silent
    Given mass with active_source CALCULATED
    When I update its estimate
    Then no AssumptionChanged is published
    And no operating point becomes DIRTY

  Scenario: An estimate edit under an active estimate fans out
    Given mass with active_source ESTIMATE
    When I update its estimate
    Then AssumptionChanged is published for "mass"
    And every non-DIRTY operating point becomes DIRTY

  Scenario: A non-OP-affecting parameter does not dirty operating points
    Given cl_max with active_source ESTIMATE
    When I update its estimate
    Then AssumptionChanged is published
    But no operating point becomes DIRTY

  Scenario: Switching the source always fans out
    Given cd0 with a calculated value
    When I switch it to CALCULATED
    Then AssumptionChanged is published
    And a recompute is scheduled

  Scenario: Switching cg_x schedules no recompute
    Given cg_x with a calculated value
    When I switch it to CALCULATED
    Then AssumptionChanged is published
    And no recompute is scheduled
    # BR-83 — cg_x is the recompute's own output

Feature: Design choices

  Scenario: A design choice can never be calculated
    When I switch g_limit to CALCULATED
    Then the response status is 422
    And the message says it is a design choice

  Scenario: A design choice never auto-switches
    Given target_static_margin with no calculated value
    When a calculated value is written with auto_switch_source true
    Then active_source is still ESTIMATE

  Scenario: Switching without a calculated value is refused
    Given cl_max with calculated_value null
    When I switch it to CALCULATED
    Then the response status is 422
    And the message says no calculated value is available

Feature: Auto-switch

  Scenario: Auto-switch happens once
    Given a parameter with no calculated value and active_source ESTIMATE
    When the first calculated value arrives with auto_switch_source true
    Then active_source becomes CALCULATED
    When the user switches back to ESTIMATE
    And a second calculated value arrives
    Then active_source stays ESTIMATE

Feature: Transport guards

  Scenario: An unknown parameter name never reaches the service
    When I PUT /aeroplanes/{id}/assumptions/thrust
    Then the response status is 422
    And no service function is called

  Scenario: NaN is rejected
    When I PUT an estimate_value of NaN
    Then the response status is 422

Feature: Computation config

  Scenario: Reading creates the row
    Given an aeroplane with no computation config
    When I GET the computation config
    Then the seven defaults are returned
    And a row now exists

  Scenario: A partial update merges
    Given a config with fine_velocity_count 8
    When I PUT {"debounce_seconds": 5.0}
    Then debounce_seconds is 5.0
    And fine_velocity_count is still 8

  Scenario: Bounds are enforced
    When I PUT {"fine_velocity_count": 1}
    Then the response status is 422
    When I PUT {"coarse_alpha_step_deg": 0}
    Then the response status is 422

  Scenario: An inverted alpha range is accepted today
    When I PUT {"coarse_alpha_min_deg": 30, "coarse_alpha_max_deg": 10}
    Then the response status is 200
    # 🔴 the resulting sweep is empty and nothing warns

Feature: Recompute job

  Scenario: No job means idle
    Given an aeroplane whose recompute has never run
    When I GET the recompute status
    Then status is "idle" and the three timestamps are null

  Scenario: A forced recompute is accepted
    When I POST /aeroplanes/{id}/recompute
    Then the response status is 202
    And the body is the job envelope
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| The effective-value rule (RF-03) | Must | Every number in the system resolves through it |
| Event gating (RF-09…RF-12) | Must | BR-27/BR-83; without it a single slider drag triggers an unbounded solver chain, and `cg_x` loops forever |
| Design-choice protection (RF-13, RF-16) | Must | BR-26; physics silently overwriting a user's stability target destroys design intent |
| Auto-switch exactly once (RF-15) | Must | BR-25; the boundary between "the system helps" and "the system overrules" |
| Idempotent seeding (RF-01, RF-02) | Must | Called on every recompute; a non-idempotent version would multiply rows per run |
| Divergence and its level (RF-04, RF-05) | Must | The only signal that an estimate has gone stale |
| Path-level name validation (RF-08) | Must | Keeps the URL space and the catalogue in lockstep |
| NaN rejection (RF-07) | Must | A NaN estimate propagates into every downstream formula |
| Computation-context read (RF-18) | Must | The read surface every consumer polls |
| Recompute job visibility (RF-19, RF-20) | Should | A UX affordance; the work happens either way |
| Computation-config CRUD (RF-21…RF-23) | Should | Tuning; sensible defaults exist |
| `warnings_count` (RF-06) | Should | A badge count, derivable client-side |
| Unit / `is_design_choice` on reads (RF-24) | Should | Display metadata |
| Seeding `min_static_margin` / `max_static_margin` | **Should (open)** | 🔴 read but never seeded |
| Cross-field validation of the α range | Should (open) | 🔴 an inverted range is silently accepted |
| Rejecting a calculated write onto a design choice | Could (open) | 🟡 only the switch is guarded |
| Collapsing the two effective-value readers into one | Should (open) | 🔴 different key type and missing-row policy |
| Writing `CG_agg` into `cg_x` | Won't | BR-28 / ADR 0011 |
| Calculating a design-choice parameter | Won't | BR-26 |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/schemas/design_assumption.py` | `VALID_PARAMETERS`, `DESIGN_CHOICE_PARAMS`, `PARAMETER_UNITS`, `PARAMETER_DEFAULTS` (`:72-108`), `compute_divergence_pct`, `divergence_level`, `AssumptionWrite`, `AssumptionSourceSwitch`, `AssumptionRead`, `AssumptionsSummary` | 🟢 |
| `app/services/design_assumptions_service.py` | `_assumption_to_read`, `get_effective_assumption` (`:66-89`), `seed_defaults` (`:92`), `list_assumptions`, `update_assumption` (`:152`), `switch_source` (`:200`), `update_calculated_value` (`:249`) | 🟢 |
| `app/models/aeroplanemodel.py` | `DesignAssumptionModel` (`:847`), `uq_assumption_aeroplane_param` | 🟢 |
| `app/models/computation_config.py` | `AircraftComputationConfigModel`, `COMPUTATION_CONFIG_DEFAULTS` (`:8-16`) | 🟢 |
| `app/schemas/computation_config.py` | `ComputationConfigRead`, `ComputationConfigWrite` | 🟢 |
| `app/api/v2/endpoints/aeroplane/design_assumptions.py` | `_PARAM_NAME_PATTERN` (`:40`), `_raise_http` (`:42-54`), the nine handlers | 🟢 |
| `app/services/mass_cg_service.py` | `get_effective_assumption_value` (`:112-128`) — the **second** reader | 🟢 / 🔴 |
| `app/core/events.py`, `app/core/background_jobs.py` | `AssumptionChanged`, `event_bus`, `job_tracker.schedule_recompute_assumptions`, `get_recompute_job` | 🟢 |
| `app/services/invalidation_service.py` | `mark_ops_dirty` | 🟢 |
