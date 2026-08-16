# operating-point-sweep

> Use-case specification, nested under the module
> [`mission-and-sizing`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: mission-and-sizing
> (R5–R11), `_reversa_sdd/data-dictionary.md` §`operating_points` /
> §`operating_pointsets`, `_reversa_sdd/domain.md` BR-21…BR-23,
> `_reversa_sdd/state-machines.md` §4.

## Overview

`operating-point-sweep` turns *design intent* into an aircraft's **operating
envelope**: fifteen flight conditions derived from the flight profile's goals
and the physics-derived stall speeds, each filtered against the aircraft's real
control capabilities, each clipped to the real hinge limits, each solved to a
trimmed state by a two-stage solver, and each persisted as an
`operating_points` row that the rest of the system reads. 🟢

It is the **only** place in `mission-and-sizing` that runs a solver, and the
only place in the codebase that runs one across a bounded process pool. 🟢

> The **single-point** solve, the trim-by-Brent path, the enrichment blocks and
> the rad/deg boundary belong to
> [`../../aero-analysis/operating-point-solve/`](../../aero-analysis/operating-point-solve/requirements.md).
> This use case owns the **set**: which points exist, at what speed, in what
> configuration, and what happens when the aircraft cannot fly one of them.

## Responsibilities

- Resolve the effective flight profile, the cruise speed (with the `V_md`
  substitution) and the reference stall speeds, recording their provenance. 🟢
- Build the fifteen target definitions from the profile goals and those
  speeds. 🟢
- Clip every flap target to the most restrictive flap-role TED, or manufacture
  no limit at all when there is none. 🟢
- Detect the aircraft's pitch / roll / yaw / flap capability from the ASB
  control-surface role tags and **skip** the targets it cannot fly. 🟢
- Solve each target: `asb.Opti` first, a velocity × α × β grid search when the
  score is poor. 🟢
- Derive turn body rates and refuse a turn the wing cannot sustain. 🟢
- Persist one `operating_points` row per solved point plus one
  `operating_pointsets` row, with the moment reference at the design CG. 🟢
- Stream the same work over SSE, committing each point as it lands, across a
  bounded process pool. 🟢

**Explicitly NOT this use case's responsibility:** the aero context it reads
(→ `aero-analysis`), the enrichment blocks it delegates to
(`trim_enrichment_service`), the operating-point CRUD and resolver
(→ `aero-analysis`), the background retrim of DIRTY rows
(→ `../../aero-analysis/retrim-invalidation/`), and the flight-profile CRUD
(→ [`../contracts.md`](../contracts.md) §C).

## Business Rules

> Global ids (`BR-*`) are inherited verbatim from
> [`../../domain.md`](../../domain.md); `BR-MS*` from
> [`../requirements.md`](../requirements.md). `BR-MS39`…`BR-MS42` are new,
> discovered while writing this specification.

- **BR-MS9 — Fifteen targets, derived from the profile goals and the reference
  stall speeds.** 🟢

  | Target | config | velocity | flap | note |
  |---|---|---|---|---|
  | `stall_near_clean` | clean | `min_speed_margin_vs_clean (1.20) · V_s1` | — | |
  | `takeoff_climb` | takeoff | `takeoff_speed_margin_vs_to (1.25) · V_s_to` | 15° | |
  | `best_angle_climb_vx` | clean | `max(1.35·V_s1, 0.85·V_cruise)` | — | read back as `v_x_mps` |
  | `best_rate_climb_vy` | clean | `max(1.50·V_s1, 0.95·V_cruise)` | — | read back as `v_y_mps` |
  | `cruise` | clean | `V_cruise` | — | |
  | `loiter_endurance` | clean | `max(1.15·V_s1, 0.80·V_cruise)` | — | |
  | `max_range` | clean | `max(1.25·V_s1, 0.95·V_cruise)` | — | |
  | `max_level_speed` | clean | `V_max` | — | descending fallback ladder |
  | `approach_landing` | landing | `approach_speed_margin_vs_ldg (1.30) · V_s0` | 30° | |
  | `stall_with_flaps` | landing | `max(2.0, 1.05·V_s0)` | 30° | needs a flap |
  | `turn_20` / `turn_40` / `turn_60` | clean | `max(V_cruise, 1.3·V_s1)` | — | `n = round(1/cos φ, 4)`; needs roll **or** yaw |
  | `dutch_role_start` | clean | `max(V_cruise, 1.3·V_s1)` | — | β = 2°; needs yaw; pre-stamped `NO_CONTROL_TRIM_MVP` |

  `V_max` defaults to `max(1.35·V_cruise, V_cruise + 8)` when the profile sets
  no `max_level_speed_mps` (BR-MS8). Altitude comes from
  `profile.environment.altitude_m` for every target. 🟢

- **BR-23 — Stall speeds come from physics, not from 0.95/0.90.** 🟢
  `_estimate_reference_speeds` precedence:

  ```
  1. context v_s1_mps  (or legacy v_stall_mps)      → provenance "polar"
       vs_to  = context v_s_to_mps  else vs_clean
       vs_ldg = context v_s0_mps    else vs_clean
       the historical 0.95 / 0.90 multipliers are DELIBERATELY not applied
       (epic gh-525 finding C1, audit §5.5 — they have no physical basis)
  2. no context at all                              → provenance "cold_start"
       vs_clean = vs_to = vs_ldg = max(3.0, V_cruise / min_speed_margin_vs_clean)
       with min_speed_margin_vs_clean floored at 1.05
  floors applied last: vs_clean ≥ 3.0 · vs_to ≥ 2.5 · vs_ldg ≥ 2.0
  ```

  On `cold_start`, `_stamp_stale_no_polar` appends `STALE_NO_POLAR` to **every**
  target, so the persisted OPs carry the audit trail (gh-535).

- **BR-22 — Flap targets clip to the real hinge limit (gh-527 / gh-536).** 🟢
  `_clip_flap_to_ted_limit` collects `(max_pos, max_neg)` from every
  **flap-role** entry in the deflection-limit map, takes the **element-wise
  minimum** across them (so the smallest surface never over-deflects), clamps
  `flap_deflection_deg` into `[−max_neg, max_pos]`, and appends
  `FLAP_DEFLECTION_CLIPPED` when `|requested| > limit + 1e-6`.
  With **no flap-role TED** no limit is manufactured — the target passes through
  untouched and the trim solver silently no-ops the missing surface. AVL has no
  internal hinge clamp and NeuralFoil silently extrapolates τ(x_h/c) past its
  training range, so an unclipped target produces over-attached flow with no
  warning.

- **BR-21 — Capability gating skips, never fails.** 🟢
  `_detect_control_capabilities` walks every `wing → xsec → control_surface`
  name through `parse_role_tag` into
  `{has_pitch_control, has_roll_control, has_yaw_control, has_flap,
  available_controls}` using

  ```
  PITCH_ROLES = {elevator, stabilator, elevon, ruddervator}
  ROLL_ROLES  = {aileron, elevon, flaperon}
  YAW_ROLES   = {rudder, ruddervator}
  FLAP_ROLES  = {flap}
  ```

  Requirements: `turn_*` needs roll **or** yaw (an explicit disjunction, not a
  set membership); `dutch_role_start` needs yaw; `stall_with_flaps` needs a
  flap. Everything else is unconditional. An unmet requirement **skips** the
  target — the run continues.
  🟡 `has_pitch_control` is computed but never required by any target, so an
  aircraft with no pitch surface still generates all fifteen and simply trims
  with an empty control set.

- **BR-MS10 — Two-stage trim, `trim_score < 0.35` ⇒ TRIMMED.** 🟢

  ```
  stage 1  asb.Opti (IPOPT), max_iter = 120, max_runtime = 0.35 s,
           behavior_on_failure = "return_last"
           α       ∈ [−8°, max(−7°, max_alpha_deg)], init min(max(3, lo), hi)
           pitch δ ∈ [−25, 25]                      (when a pitch role exists)
           roll δ  ∈ [−20, 20]                      (turn targets only)
           yaw δ   ∈ [−25, 25]                      (turn + dutch targets)
           flap    = the clipped fixed value, NOT an optimiser variable
           objective = 50·Cm² + 3·CY²
                       [+ 15·(CL − CL_target)²]        when CL_target exists
                       [+ 2·Cl² + 2·Cn²]               turn targets
                       + 0.001·Σδ²                     control-effort penalty
           any exception ⇒ the candidate is None and stage 2 runs

  stage 2  grid search, only when the stage-1 score > 0.35
           velocities × α = linspace(−4°, 20°, 13) × β candidates
           → updates BOTH α and the velocity                        (gh-528)

  trim_score = |Cm| + 0.5·|CY| [+ 0.3·|CL − CL_target|]
  CL_target  = m·g·n / (q·S_ref),  q = ½·ρ·max(V, 1e-3)²;  None without mass or S_ref
  status     = TRIMMED if score < 0.35 else NOT_TRIMMED (+ a "NOT_TRIMMED" warning)
               LIMIT_REACHED when |α| > max_alpha_deg or |β| > max_beta_deg
               (+ ALPHA_LIMIT_REACHED / BETA_LIMIT_REACHED)
  ```

- **BR-MS40 — The fallback velocity ladder is direction-aware.** 🟢
  `_fallback_speeds(name, base)` returns
  `[max(2.0, base·f) for f in factors]` with
  `factors = [1.0, 0.95, 0.90, 0.85]` for `max_level_speed` and
  `[1.0, 1.05, 1.10, 1.15]` for every other target — a top-speed point is
  retried **slower**, everything else **faster**, because that is the direction
  in which each becomes trimmable. The `2.0 m/s` floor applies to both.

- **BR-MS11 — The solver path lives on `trim_method`, never in
  `trim_residuals` (gh-627).** 🟢 `trim_method ∈ {"opti", "grid_fallback"}`;
  `trim_residuals` is typed `dict[str, float]` and Pydantic-rejects strings.

- **BR-MS12 — Turn feasibility is checked before the solution is trusted.** 🟢
  A `bank_deg` target derives `(p, q, r)` from `turn_kinematics` (rounded to 6
  decimals) and `n = 1/cos φ`. When `V < V_s1 · √n` the point is set to
  `LIMIT_REACHED` and a `STALL_IN_TURN` warning is appended — otherwise the
  trimmer would happily return a converged solution at the wrong load factor.
  🔴 The warning is a **formatted sentence**, not the bare tag:
  `"STALL_IN_TURN: required CL at 60 deg bank (n=2.00) exceeds CL_max — V=14.0
  < V_stall_turn=17.0 m/s"`. Every other warning in the list is a bare token, so
  a consumer matching on equality misses this one; prefix matching is required.

- **BR-MS13 — Parallelism uses processes, not threads (gh-867).** 🟢 The
  CasADi/IPOPT solve does **not** release the GIL (a thread pool benchmarked at
  0.35–0.89×), so the **streaming** path uses a module-level bounded
  `ProcessPoolExecutor` (spawn context,
  `max_workers = max(1, min(4, cpu − 1))`) with BLAS pinned to one thread per
  worker (`OMP` / `OPENBLAS` / `MKL` / `VECLIB_MAXIMUM` / `NUMEXPR_NUM_THREADS
  = 1`, applied to the parent env at spawn **and** in the initializer, then
  restored) → ≈ 2.9× at 4 workers. Workers receive a picklable
  `_WorkerSolveCtx` (the `asb.Airplane` pickles cleanly; the SQLAlchemy model
  does not, so only `total_mass_kg` crosses via `_AircraftMassOnly`) and
  **never touch the database**. The main thread owns persistence and yields in
  `as_completed` order. A worker exception is logged and yields
  `(target, None)` — one bad target never kills the run.
  The **non-streaming** batch path stays **sequential on purpose** so its
  contract and its many solver mocks are unchanged.

- **BR-MS14 / BR-MS39 — The SSE contract, and what `skip` really means.** 🟢
  Events: `targets` → one `op` per solved point → `done`, with `error` for a
  setup failure and `skip` for a point that came back `None`.
  🔴 **`skip` is not the capability signal.** The streaming path filters
  `supported = [t for t in targets if _validate_target_capability(t)[0]]`
  **before** emitting `targets`, so a capability-gated target never appears in
  the stream at all — no `targets` entry, no `skip`, no reason. A `skip` is
  emitted only when a worker solve raised or returned `None`, and it carries
  just `{"name": …}` with no reason field. The client therefore cannot
  distinguish "your aircraft has no rudder" (silent) from "this target failed to
  solve" (`skip`).

- **BR-MS41 — `replace_existing` is aircraft-wide, not set-scoped.** 🟢
  `_clear_existing_op_sets` deletes **every** `operating_pointsets` row **and
  every** `operating_points` row of the aircraft — including manually created
  points and points belonging to other sets.

- **BR-MS42 — The streaming path owns its own commits.** 🟢 It creates and
  **commits** the empty point-set row before the `targets` event, then commits
  after every inserted point, so a dropped connection leaves a valid partial
  set. This is a deliberate exception to BR-78 / ADR 0009 (`get_db()` owns the
  transaction boundary); the batch path obeys the rule and only flushes.

- **BR-MS7 — "No profile assigned" is load-bearing.** 🟢
  `_load_effective_flight_profile` returns `(profile_dict, source_profile_id)`;
  with no assignment it returns `_default_profile()` and
  `source_profile_id = None`, which makes
  `_resolve_cruise_speed_with_md_fallback` substitute `V_md` from the cached
  context. The resolved cruise speed is written back into
  `profile["goals"]["cruise_speed_mps"]` before the targets are built, so every
  velocity derived from `V_cruise` follows.

- **BR-14 — The sweep reads the single-source context.** 🟢 `v_s1_mps`,
  `v_s_to_mps`, `v_s0_mps`, `v_stall_mps`, `v_md_mps` — nothing here re-derives
  a polar.

- **BR-19/BR-20 (inherited)** — the persisted rows are what
  `resolve_operating_point` later loads, so `alpha`/`beta` are stored in
  **radians** and `xyz_ref` is `[design_cg_x, 0, 0]`.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Resolve the effective profile, falling back to `_default_profile()` | Must | No assignment ⇒ the documented defaults and `source_profile_id = None` |
| RF-02 | Honour `profile_id_override` | Should | The named profile is used and recorded on the point set |
| RF-03 | Substitute `V_md` for the cruise speed when no profile is assigned | Must | Every derived velocity follows the substituted value |
| RF-04 | Default `V_max` to `max(1.35·V_cruise, V_cruise + 8)` | Must | Only when the profile sets no `max_level_speed_mps` |
| RF-05 | Prefer per-configuration stall speeds from the context | Must | `v_s_to` equals the context value, not `0.95·v_s1` |
| RF-06 | Fall back to the clean stall for all three configurations on a legacy context | Must | Only `v_stall_mps` present ⇒ three identical values |
| RF-07 | Cold-start fallback `max(3.0, V_cruise / margin)` with `provenance="cold_start"` | Must | No context ⇒ the documented value |
| RF-08 | Apply the floors 3.0 / 2.5 / 2.0 last | Must | A 1 m/s context stall becomes 3.0 clean, 2.5 takeoff, 2.0 landing |
| RF-09 | Stamp `STALE_NO_POLAR` on every target on a cold start | Must | All fifteen carry it |
| RF-10 | Generate exactly the fifteen documented targets | Must | Name, config, velocity and flap match the table |
| RF-11 | Derive turn `n` as `round(1/cos φ, 4)` | Must | `turn_60` ⇒ `2.0` |
| RF-12 | Clip a flap target to the most restrictive flap TED | Must | 25° and 30° flaps ⇒ a 30° request clips to 25° with `FLAP_DEFLECTION_CLIPPED` |
| RF-13 | Manufacture no flap limit when no flap TED exists | Must | The target passes through unclipped and unwarned |
| RF-14 | Not warn when the request is already within the limit | Should | A 15° request against a 25° limit adds no warning |
| RF-15 | Detect capabilities from the ASB role tags | Must | The four booleans and the sorted, de-duplicated `available_controls` |
| RF-16 | Skip a target whose capability requirement is unmet | Must | No roll and no yaw ⇒ the three turn targets are skipped, not failed |
| RF-17 | Treat the turn requirement as roll **or** yaw | Must | Rudder-only aircraft still get the turn targets |
| RF-18 | Solve stage 1 with `asb.Opti` under the documented bounds and objective | Must | `trim_method == "opti"` on success |
| RF-19 | Treat an `Opti` exception as a failed candidate, not a failed run | Must | The grid fallback runs and the point is still produced |
| RF-20 | Run the grid fallback only when the score exceeds 0.35 | Must | A good `Opti` solve issues no extra solver calls |
| RF-21 | Update **both** α and the velocity in the grid fallback | Must | gh-528: the fallback is not α-only |
| RF-22 | Search a descending velocity ladder for `max_level_speed` | Should | `[1.0, 0.95, 0.90, 0.85]`, floored at 2 m/s |
| RF-23 | Mark `LIMIT_REACHED` on an α or β bound | Must | With the matching warning token |
| RF-24 | Mark a stall in a turn `LIMIT_REACHED` with `STALL_IN_TURN` | Must | `V < V_s1·√n` |
| RF-25 | Keep `trim_residuals` numeric-only and the path on `trim_method` | Must | A string fails validation (gh-627) |
| RF-26 | Persist one OP row per solved point with `xyz_ref = [design_cg_x, 0, 0]` | Must | On every row |
| RF-27 | Persist one point-set row named `default_operating_point_set` | Must | Carrying the id list and `source_flight_profile_id` |
| RF-28 | Optionally clear the aircraft's existing sets and points | Should | `replace_existing = true` removes **all** of them |
| RF-29 | Stream over SSE, committing each point as it is solved | Should | A dropped connection leaves a valid partial set |
| RF-30 | Parallelise the streaming path with processes, not threads | Should | ≈ 2.9× at 4 workers; workers never open a DB session |
| RF-31 | Pin BLAS to one thread per worker and restore the parent env | Should | No oversubscription; the parent's env is unchanged afterwards |
| RF-32 | Survive a single failed target | Must | It yields `skip`; the remaining points are still produced |
| RF-33 | Keep the non-streaming batch path sequential | Must | Its contract and mocks are unchanged |
| RF-34 | Report a setup failure as an SSE `error` event, not a 500 | Should | The stream ends cleanly |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Performance | Processes, not threads, because CasADi/IPOPT holds the GIL (a thread pool measured 0.35–0.89×) | gh-867, `operating_point_generator_service.py:1188-1252` | 🟢 |
| Performance | BLAS pinned to one thread per worker prevents oversubscription | `_BLAS_THREAD_ENV`, `_opg_worker_init` | 🟢 |
| Performance | The executor is module-level and lock-guarded, so the pool is created once | `_opg_executor`, `_opg_executor_lock` | 🟢 |
| Performance | Stage 1 is time-boxed at `max_runtime = 0.35 s` per target | `opti.solve` | 🟢 |
| Performance | The grid fallback is skipped entirely on a good stage-1 solve | `_trim_or_estimate_point` | 🟢 |
| Scalability | `max_workers = max(1, min(4, cpu − 1))` bounds the pool | `_opg_worker_count` | 🟢 |
| Isolation | Workers never touch the database; only `total_mass_kg` crosses the process boundary | `_WorkerSolveCtx`, `_AircraftMassOnly` | 🟢 |
| Robustness | Capability gating **skips** rather than failing the whole generation | BR-21 | 🟢 |
| Robustness | A worker exception yields `(target, None)` instead of aborting | `_solve_targets_in_parallel` | 🟢 |
| Robustness | An enrichment failure is logged and the point is still returned | `_solve_and_enrich` | 🟢 |
| Robustness | A setup failure becomes an SSE `error` event rather than a 500 | streaming generator | 🟢 |
| Durability | Each SSE point is committed **before** its event is emitted | same | 🟢 |
| Traceability | Every generated OP carries `provenance`-derived warnings and its `trim_method` / `trim_score` | `_stamp_stale_no_polar`, `TrimmedPoint` | 🟢 |
| Correctness | Flap targets clip to the real hinge limit because neither AVL nor NeuralFoil clamps | gh-527/gh-536 | 🟢 |
| Correctness | `trim_residuals` is float-typed so the solver path cannot leak into it | gh-627 | 🟢 |
| Correctness | Turn feasibility is checked before the trim is trusted | `_apply_turn_feasibility` | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Target generation

  Scenario: Fifteen targets from the profile
    Given a default flight profile and a full control set
    When the default point set is generated
    Then 15 targets are produced with the documented velocities and configs

  Scenario: The cruise speed drives the derived velocities
    Given a profile whose cruise speed is 20 m/s and V_s1 is 10 m/s
    Then best_angle_climb_vx is at max(13.5, 17.0) = 17.0 m/s
    And loiter_endurance is at max(11.5, 16.0) = 16.0 m/s

  Scenario: No profile means best-glide cruise
    Given an aeroplane with no flight profile assigned
    And a cached context whose v_md_mps is 14.0
    Then the cruise target is at 14.0 m/s
    And every velocity derived from V_cruise follows

  Scenario: V_max defaults when the profile omits it
    Given a profile with cruise 20 m/s and no max_level_speed_mps
    Then max_level_speed is at max(27.0, 28.0) = 28.0 m/s

  Scenario: Turn load factors
    Then turn_20, turn_40 and turn_60 carry n of 1.0642, 1.3054 and 2.0

Feature: Reference speeds

  Scenario: Stall speeds come from the polar
    Given a context with v_s1 12.0, v_s_to 11.0 and v_s0 10.0
    Then the takeoff target uses 11.0, not 0.95 times 12.0
    And the provenance is "polar"

  Scenario: A legacy context reuses the clean value
    Given a context with only v_stall_mps 12.0
    Then all three reference speeds are 12.0
    And the 0.95 and 0.90 multipliers are not applied

  Scenario: Cold start stamps every target
    Given no computation context
    Then the reference speeds are max(3.0, V_cruise / margin)
    And the provenance is "cold_start"
    And every generated operating point carries STALE_NO_POLAR

  Scenario: Floors apply last
    Given a context whose v_s1 is 1.0
    Then vs_clean is 3.0, vs_to is 2.5 and vs_ldg is 2.0

Feature: Flap clipping

  Scenario: The most restrictive surface governs
    Given two flap TEDs limited to 25 and 30 degrees
    When a landing target requests 30 degrees
    Then the target is clipped to 25
    And FLAP_DEFLECTION_CLIPPED is appended

  Scenario: A request inside the limit is not warned
    Given a flap TED limited to 25 degrees
    When a takeoff target requests 15 degrees
    Then the value is unchanged
    And no warning is appended

  Scenario: No flap TED means no manufactured limit
    Given an aircraft with no flap-role TED
    Then the flap target passes through unclipped
    And the trim solver no-ops the missing surface

Feature: Capability gating

  Scenario: Missing capabilities skip, not fail
    Given an aircraft with neither roll nor yaw control
    Then the three turn targets and the dutch-roll target are skipped
    And the remaining eleven are generated normally

  Scenario: A rudder alone is enough to turn
    Given an aircraft with a rudder and no aileron
    Then the three turn targets are generated

  Scenario: Flaps gate only their own target
    Given an aircraft with no flap-role TED
    Then stall_with_flaps is skipped
    But approach_landing and takeoff_climb are still generated

Feature: The two-stage trim

  Scenario: A good Opti solve skips the grid
    Given a target whose Opti solve scores 0.12
    Then trim_method is "opti"
    And no grid-search evaluation is performed

  Scenario: The grid fallback moves velocity too
    Given a target whose Opti solve scores above 0.35
    When the grid fallback runs
    Then both alpha and the velocity are updated
    And trim_method is "grid_fallback"

  Scenario: A top-speed point is retried slower
    Given the max_level_speed target enters the fallback at 28 m/s
    Then the candidate velocities are 28.0, 26.6, 25.2 and 23.8

  Scenario: An Opti exception is not a run failure
    Given asb.Opti raises for one target
    Then the grid fallback produces the point
    And the remaining targets are unaffected

  Scenario: The status thresholds
    Given a trim score of 0.34
    Then the status is TRIMMED
    And with 0.36 it is NOT_TRIMMED with a NOT_TRIMMED warning

  Scenario: An alpha bound is a limit
    Given max_alpha_deg 15 and a solved alpha of 18
    Then the status is LIMIT_REACHED
    And ALPHA_LIMIT_REACHED is appended

  Scenario: A stall in a turn is caught
    Given a 60 degree bank target whose velocity is below V_s1 times sqrt(2)
    Then the point is LIMIT_REACHED
    And a warning beginning with STALL_IN_TURN is appended
    # 🔴 the warning is a sentence, not the bare token

  Scenario: The solver path never enters the residuals
    Given a completed trim
    Then trim_method carries the path
    And trim_residuals contains only floats

Feature: Persistence

  Scenario: The moment reference is the design CG
    Then every persisted operating point has xyz_ref of [design_cg_x, 0, 0]

  Scenario: Angles are stored in radians
    Given a solved alpha of 5 degrees
    Then the stored alpha is about 0.0873

  Scenario: replace_existing clears everything
    Given an aircraft with a manually created operating point
    When I generate with replace_existing true
    Then the manual point is gone
    # 🔴 aircraft-wide, not set-scoped

Feature: Streaming

  Scenario: The stream commits incrementally
    Given a generation stream that is interrupted after three op events
    Then three operating points are persisted
    And the point set references exactly those three

  Scenario: Events arrive in completion order
    Then the op events are not guaranteed to follow the target order

  Scenario: A failed target is skipped, not fatal
    Given one target whose worker solve raises
    Then a skip event names it
    And the remaining targets still produce op events

  Scenario: A capability-gated target is invisible
    Given an aircraft with no rudder
    When I stream a generation
    Then dutch_role_start appears in neither targets nor skip
    # 🔴 the client cannot tell why it is missing

  Scenario: A setup failure is an event, not a 500
    Given an unknown aeroplane UUID
    Then the response is 200 with a single error event
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| The fifteen targets and their velocities (RF-10, RF-11) | Must | The aircraft's entire operating envelope; every downstream chart reads these rows |
| Physics-derived stall speeds (RF-05…RF-08) | Must | BR-23; the 0.95/0.90 heuristic had no physical basis and biased every low-speed target |
| Cold-start stamping (RF-09) | Must | Without it, estimated points are indistinguishable from measured ones |
| Flap clipping (RF-12…RF-14) | Must | An unclipped flap produces silently wrong aerodynamics — no solver warns |
| Capability gating (RF-15…RF-17) | Must | BR-21; failing the run because an aircraft has no rudder would block every glider |
| The two-stage trim (RF-18…RF-23) | Must | Produces the persisted trim state the rest of the system reads |
| Turn feasibility (RF-24) | Must | Otherwise a converged solution is returned at the wrong load factor |
| `trim_method` / `trim_residuals` typing (RF-25) | Must | gh-627 broke every OP enrichment |
| Persistence shape (RF-26, RF-27) | Must | `xyz_ref` at the design CG is what makes `Cm` meaningful |
| `V_md` substitution (RF-03) | Must | BR-MS7; it moves every derived velocity |
| SSE streaming and incremental commit (RF-29, RF-34) | Should | A responsiveness feature; the batch path remains correct |
| Process-pool parallelism (RF-30, RF-31) | Should | A 2.9× speed-up on a UI-blocking operation |
| Sequential batch path (RF-33) | Must | Preserving the existing contract and its mocks |
| `profile_id_override` (RF-02) | Should | A what-if affordance |
| `replace_existing` (RF-28) | Should | Regeneration; the default is additive |
| Emitting a `skip` **with a reason** for capability-gated targets | **Must (open)** | 🔴 today they vanish silently |
| A bare `STALL_IN_TURN` token alongside the sentence | Should (open) | 🔴 the only formatted warning in the list |
| Scoping `replace_existing` to the generated set | Should (open) | 🔴 it deletes manual points today |
| Varying control surfaces in the grid fallback | **Won't** | 🟢 decided (`Q-MS-5`): no deflection grid; the defect is elsewhere. `best_controls = {}` — the fallback trims by α/β/V only |
| Parallelising the batch path | Won't | RF-33; the mocks and the contract depend on sequential execution |
| Requiring pitch control for any target | Won't (today) | 🟡 `has_pitch_control` is detected but never enforced |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/operating_point_generator_service.py` | `PITCH/ROLL/YAW/FLAP_ROLES` (`:48-51`), `_clip_flap_to_ted_limit` (`:54`), `TrimmedPoint` (`:118`), `_op_turn_rates` (`:141`), `_apply_turn_feasibility` (`:156`), `_compute_trim_score` (`:192`), `_default_profile` (`:199`), `_load_design_cg_x` (`:230`), `_load_effective_mass_kg` (`:249`), `_resolve_cruise_speed_with_md_fallback` (`:271`), `_load_effective_flight_profile` (`:287`), `_estimate_reference_speeds` (`:313`), `_stamp_stale_no_polar` (`:367`), `_build_target_definitions` (`:392`), `_fallback_speeds` (`:513`), `_pick_control_name` (`:521`), `_detect_control_capabilities` (`:533`), `_required_capabilities_for_target` (`:557`), `_validate_target_capability` (`:567`), `_solve_trim_candidate_with_opti` (`:585`), `_evaluate_trim_candidate` (`:708`), `_cl_target_for_velocity` (`:784`), `_grid_search_trim` (`:800`), `_apply_limit_warnings` (`:845`), `_trim_or_estimate_point` (`:872`), `_op_model_from_point` (`:1009`), `_clear_existing_op_sets` (`:1033`), `_persist_point_set` (`:1042`), `_GenerationContext` (`:1075`), `_prepare_generation` (`:1092`), `_solve_and_enrich` (`:1133`), the pool block (`:1188-1265`), `_WorkerSolveCtx` (`:1268`), `_AircraftMassOnly` (`:1285`), `_solve_targets_in_parallel` (`:1332`), `generate_default_set_for_aircraft` (`:1354`), `_sse` (`:1413`), `generate_default_set_stream_for_aircraft` (`:1418`) | 🟢 |
| `app/services/turn_kinematics.py` | `turn_kinematics` — `(p, q, r)` and `n` | 🟢 |
| `app/services/control_surface_mixing.py` | `parse_role_tag`, `build_deflection_limits_from_schema`, `build_mix_params_from_schema` | 🟢 |
| `app/services/trim_enrichment_service.py` | `compute_enrichment` — called best-effort | 🟢 |
| `app/schemas/aeroanalysisschema.py` | `GenerateOperatingPointSetRequest` (`:397`), `GeneratedOperatingPointSetRead` (`:438`), `StoredOperatingPointRead` | 🟢 |
| `app/models/analysismodels.py` | `OperatingPointModel` (`:20`), `OperatingPointSetModel` (`:6`) | 🟢 |
| `app/api/v2/endpoints/operating_points.py` | `generate_default_operating_point_set` (`:100`), `…_stream` (`:126`) | 🟢 |
| `app/converters/model_schema_converters.py` | `aeroplane_model_to_aeroplane_schema_async`, `aeroplane_schema_to_asb_airplane_async` | 🟢 |
