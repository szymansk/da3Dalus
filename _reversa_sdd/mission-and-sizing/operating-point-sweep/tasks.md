# operating-point-sweep — Implementation Tasks

> Executable sequence to re-implement this use case from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker (🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP).
> Parent: [`../tasks.md`](../tasks.md) T-05.
> Contracts: [`../contracts.md`](../contracts.md) §D.

## Prerequisites

- [ ] **AeroSandbox ≥ 4.0.7** with `Opti` (IPOPT/CasADi), `AeroBuildup`,
      `OperatingPoint`, `Atmosphere`, and an `Airplane` that **pickles cleanly**
      — the process pool depends on it.
- [ ] `wing-design`: `parse_role_tag`,
      `build_deflection_limits_from_schema(plane_schema) -> {name: (max_pos,
      max_neg)}`, `build_mix_params_from_schema`, and the model→schema→ASB
      converters.
- [ ] `aero-analysis`: the `OperatingPointStatus` enum
      (`NOT_TRIMMED` / `COMPUTING` / `TRIMMED` / `LIMIT_REACHED` / `DIRTY` /
      `INVALID`), `trim_enrichment_service.compute_enrichment`, and the
      `operating_points` / `operating_pointsets` tables.
- [ ] [`../design-assumptions/`](../design-assumptions/tasks.md): the effective
      `mass` and `cg_x` reads.
- [ ] `mission-and-sizing` flight profiles ([`../tasks.md`](../tasks.md) T-04)
      including `_default_profile()` and the `V_md` substitution.
- [ ] `app/services/turn_kinematics.turn_kinematics(bank_deg, velocity)`
      returning `p`, `q`, `r` and `n`.
- [ ] `platform-core`: SSE plumbing, and a FastAPI lifespan hook to call
      `shutdown_opg_executor()`.
- [ ] A CI **fast-tier** strategy: this is the only solver-bound use case in the
      module, so every task below needs a test that stubs
      `asb.Opti` / `asb.AeroBuildup` at the boundary (ADR 0015).

## Tasks

- [ ] **T-01 — Reference speeds with provenance.**
  Implement `_estimate_reference_speeds` exactly as
  [`design.md`](design.md) §Reference speeds: prefer `v_s1_mps`, fall back to
  the legacy `v_stall_mps`, reuse the clean value for the two missing
  configurations, cold-start to `max(3.0, V_cruise / max(1.05, margin))`, and
  apply the floors `3.0 / 2.5 / 2.0` **last**. Return the `provenance` tag.
  - Legacy origin: `app/services/operating_point_generator_service.py:313-365`
  - Definition of done: the historical `0.95` / `0.90` multipliers appear
    nowhere; a context value of `0` or a negative is treated as absent; the
    floors are applied after the selection, not before.
  - Confidence: 🟢

- [ ] **T-02 — Cold-start stamping.**
  `_stamp_stale_no_polar(targets, refs)` — a no-op unless
  `provenance == "cold_start"`, otherwise a **copy** of every target with
  `STALE_NO_POLAR` appended idempotently.
  - Legacy origin: `:367-390`
  - Definition of done: all fifteen targets carry the tag on a cold start; none
    on the polar path; the input list is not mutated.
  - 🟡 The `provenance` itself is not persisted — only its consequence. Consider
    storing it on the row so a consumer can tell `polar` from `cold_start`
    without string-matching a warning.
  - Confidence: 🟢

- [ ] **T-03 — The fifteen target definitions.**
  `_build_target_definitions(profile, refs)` producing the table in
  [`requirements.md`](requirements.md) BR-MS9, with
  `n_target = round(1/cos(radians(bank)), 4)` for the three turns,
  `beta_target_deg = 2.0` and a pre-stamped `NO_CONTROL_TRIM_MVP` on
  `dutch_role_start`, `flap_deflection_deg` 15° / 30° before clipping, the
  `max(2.0, 1.05·V_s0)` floor on `stall_with_flaps`, and
  `altitude = profile.environment.altitude_m` on all fifteen.
  - Legacy origin: `:392-510`
  - Definition of done: fifteen dicts, names and configs exactly as tabulated;
    `turn_60` carries `n_target = 2.0`; a profile with cruise 20 and `V_s1` 10
    reproduces the documented velocities.
  - 🔴 **Deviation to decide:** `goals.target_turn_n` and `goals.loiter_s` are
    validated on the profile schema but never read here — the banks are
    hard-coded and the loiter point is a speed, not a duration. Either consume
    them or drop them from the profile.
  - Confidence: 🟢

- [ ] **T-04 — Flap clipping to the most restrictive TED.**
  `_clip_flap_to_ted_limit`: collect `(max_pos, max_neg)` from every flap-role
  entry, take the **element-wise minimum** (gh-536), clamp into
  `[−max_neg, max_pos]`, append `FLAP_DEFLECTION_CLIPPED` only when
  `|requested| > limit + 1e-6`, and **return the target unchanged when no
  flap-role entry exists**.
  - Legacy origin: `:54-115`
  - Definition of done: 25° and 30° flaps clip a 30° request to 25° with the
    warning; a 15° request against a 25° limit is untouched and unwarned; no
    flap TED ⇒ byte-identical target; the warning is idempotent.
  - 🟡 The function returns the same object when unchanged and a copy when
    clipped — make it always copy, or document the identity contract.
  - Confidence: 🟢

- [ ] **T-05 — Capability detection and gating.**
  `_detect_control_capabilities` walking `wings → xsecs → control_surfaces`
  through `parse_role_tag` into the four booleans plus a sorted, de-duplicated
  `available_controls`; `_validate_target_capability` implementing the turn
  disjunction (roll **or** yaw) before the generic requirement lookup.
  - Legacy origin: `:521-583`
  - Definition of done: an elevon sets both pitch and roll; a ruddervator sets
    both pitch and yaw; a rudder-only aircraft still gets the three turn
    targets; a flapless aircraft loses `stall_with_flaps` but keeps
    `approach_landing`; an empty or whitespace control name is ignored.
  - 🟡 `has_pitch_control` is computed but never required. Decide whether a
    pitchless aircraft should skip everything, or keep the current
    "generate and trim with nothing" behaviour.
  - Confidence: 🟢

- [ ] **T-06 — Stage 1: the `Opti` trim candidate.**
  Implement `_solve_trim_candidate_with_opti` per
  [`design.md`](design.md) §Stage 1 — the α variable and its bounds, the three
  conditional control variables, the **fixed** flap deflection applied through
  `with_control_deflections`, the `asb.OperatingPoint` with `(p, q, r)` from
  `_op_turn_rates`, one
  `AeroBuildup(...).run_with_stability_derivatives()` call, the six-term
  objective, and `solve(max_iter=120, max_runtime=0.35,
  behavior_on_failure="return_last")`. **Any** exception returns `None`.
  - Legacy origin: `:585-706`
  - Definition of done: a solved candidate reports α, β, score, controls and the
    three metrics; a raising solver returns `None` and does not propagate;
    flap deflection never appears among the optimiser variables.
  - 🟡 Name the six weights (`_W_CM = 50.0`, …) — none is documented today.
  - Confidence: 🟢

- [ ] **T-07 — Scoring and the CL target.**

  ```
  _compute_trim_score(cm, cy, cl, cl_target) = |Cm| + 0.5·|CY|
                                               [+ 0.3·|CL − CL_target|]
  _cl_target_for_velocity(V, m, S_ref, ρ, n):
      None when m is falsy or S_ref <= 0 or q <= 1e-6
      else m·9.81·n / (½·ρ·max(V, 1e-3)²·S_ref)
  ```

  - Legacy origin: `:192-197`, `:784-798`
  - Definition of done: with no mass the CL term drops out of both the objective
    and the score; a `turn_60` target's CL target is twice the level-flight one
    at the same speed.
  - Confidence: 🟢

- [ ] **T-08 — Stage 2: the grid fallback (gh-528).**
  `_grid_search_trim` over `_fallback_speeds(name, V)` × β candidates ×
  `linspace(−4°, 20°, 13)`, tracking the best `(score, α, β, V)`. A failing
  candidate is logged at DEBUG and skipped, never fatal.
  `_fallback_speeds` returns `[max(2.0, base·f)]` with **descending** factors
  `[1.0, 0.95, 0.90, 0.85]` for `max_level_speed` and ascending
  `[1.0, 1.05, 1.10, 1.15]` otherwise.
  - Legacy origin: `:513-518`, `:800-843`
  - Definition of done: the returned velocity may differ from the input (gh-528
    regression); `max_level_speed` is retried slower; every candidate uses the
    CL target **at its own velocity**, not the original one.
  - 🔴 **Deviation to decide:** `best_controls` is reset to `{}` on every
    improvement and always returned empty, so the fallback trims by α/β/V only.
    A target that needs a different deflection cannot be reached at all. Either
    search a coarse control grid, or report the point as
    "not reachable with the available authority" instead of `NOT_TRIMMED`.
  - Confidence: 🟢

- [ ] **T-09 — Status and limit warnings.**
  `_apply_limit_warnings`: `TRIMMED` below `0.35`, otherwise `NOT_TRIMMED` with
  a `"NOT_TRIMMED"` warning; then `|α| > max_alpha_deg` ⇒ `LIMIT_REACHED` +
  `ALPHA_LIMIT_REACHED` and `|β| > max_beta_deg` ⇒ `LIMIT_REACHED` +
  `BETA_LIMIT_REACHED`. The limit check runs **after** the score check, so it
  overrides `TRIMMED`.
  - Legacy origin: `:845-869`
  - Definition of done: score `0.34` ⇒ TRIMMED; `0.36` ⇒ NOT_TRIMMED with the
    warning; a converged solve outside the α envelope is `LIMIT_REACHED`, not
    `TRIMMED`; a `None` bound disables that check.
  - Confidence: 🟢

- [ ] **T-10 — Turn kinematics and feasibility.**
  `_op_turn_rates` returning zeros for a non-turn and `turn_kinematics(bank,
  V)` rounded to 6 decimals otherwise; `_apply_turn_feasibility` setting
  `LIMIT_REACHED` and appending the `STALL_IN_TURN` message when
  `V < vs_clean · √n`.
  - Legacy origin: `:141-179`
  - Definition of done: a 60° bank at `V < V_s1·√2` is `LIMIT_REACHED`; a
    feasible turn is untouched; `vs_clean <= 0` disables the check.
  - 🔴 **Deviation required:** emit a bare `"STALL_IN_TURN"` token **alongside**
    the human sentence (or move the numbers into a structured field). Every
    other warning is a bare token, so a consumer matching on equality misses
    this one today.
  - Confidence: 🟢

- [ ] **T-11 — The two-stage orchestration.**
  `_trim_or_estimate_point`: seed `warnings` from the target, run stage 1, run
  stage 2 **only** when the stage-1 candidate is `None` or scores above `0.35`,
  apply the limit warnings, build the `TrimmedPoint` with `alpha_rad` /
  `beta_rad`, the generated `description`
  (`config=…, target_n=…, V=…, altitude=…`), `trim_method`, `trim_score`,
  `trim_residuals` (**floats only**, gh-627) and `aero_coefficients` (gh-861,
  finite CL/CD/Cm so the comparison table can show L/D instead of "—").
  - Legacy origin: `:872-1003`
  - Definition of done: a good stage-1 solve issues **no** grid evaluations
    (assert on a mocked solver's call count); `trim_method` is `"opti"` or
    `"grid_fallback"`; a string in `trim_residuals` fails validation.
  - Confidence: 🟢

- [ ] **T-12 — `_prepare_generation`, the resolution pipeline.**
  The eight steps of [`design.md`](design.md) §Main Flow, in order — crucially:
  the resolved cruise speed is **written back** into
  `profile["goals"]["cruise_speed_mps"]` before the targets are built, and
  `asb_airplane.xyz_ref = [design_cg_x, 0, 0]` is set **before** any solve.
  - Legacy origin: `:1092-1130`
  - Definition of done: with no profile assigned, *every* velocity derived from
    `V_cruise` follows `v_md_mps`, not only the `cruise` target; `Cm` changes
    with `design_cg_x` at unchanged geometry.
  - 🟡 `build_deflection_limits_from_schema` is called **twice** on the same
    schema (once for clipping, once for the context) — compute it once.
  - Confidence: 🟢

- [ ] **T-13 — `_solve_and_enrich`.**
  Capability check → `_trim_or_estimate_point` → `_apply_turn_feasibility` →
  best-effort `compute_enrichment` (a failure is logged with `exc_info` and the
  point is still returned). An unsupported target logs a WARNING naming the
  missing capability **and** the available controls, then returns `None`.
  - Legacy origin: `:1133-1186`
  - Definition of done: an enrichment exception never loses the point; the skip
    log names both sides.
  - Confidence: 🟢

- [ ] **T-14 — Persistence.**
  `_op_model_from_point` (α/β in **radians**, `xyz_ref = [design_cg_x, 0, 0]`,
  `status = point.status.value`), `_clear_existing_op_sets`, and
  `_persist_point_set` inserting the rows, flushing for ids, then one
  `operating_pointsets` row named `default_operating_point_set` whose
  `operating_points` JSON column holds the id list and whose
  `source_flight_profile_id` records the profile.
  - Legacy origin: `:1009-1073`
  - Definition of done: every row carries the design CG as its moment
    reference; a 5° α reads back as ≈ 0.0873 rad; the set name and description
    are exact.
  - 🔴 **Deviation to decide:** `_clear_existing_op_sets` deletes **all**
    operating points and sets of the aircraft, including manually created ones.
    Scope it to the generated set, or rename the flag to say what it does.
  - 🟡 The id list has no referential integrity — consider a real association
    table.
  - Confidence: 🟢

- [ ] **T-15 — The sequential batch path.**
  `generate_default_set_for_aircraft`: `_prepare_generation`, a sequential
  walrus comprehension over `ctx.targets`, `_persist_point_set`, flush, refresh
  each row, return `GeneratedOperatingPointSetRead`. `NotFoundError` and
  `ValidationError` propagate; `SQLAlchemyError` and everything else become
  `InternalError`.
  - Legacy origin: `:1354-1411`
  - Definition of done: **stays sequential** — the existing solver mocks and the
    contract depend on it; the summary log reports `generated=N / M targets`.
  - Confidence: 🟢

- [ ] **T-16 — The bounded process pool (gh-867).**
  `_BLAS_THREAD_ENV` (five variables), a `spawn` context, a module-level
  executor behind a lock, `_opg_worker_count() = max(1, min(4, cpu − 1))`,
  `_opg_worker_init` re-applying the pins inside each worker, the parent env set
  **before** creation and **restored** afterwards, a `_opg_noop` warm-up task,
  and `shutdown_opg_executor()` for the lifespan.
  - Legacy origin: `:1188-1265`
  - Definition of done: the parent's environment is unchanged after pool
    creation; the pool is created once under concurrent callers; workers report
    `OMP_NUM_THREADS == "1"`.
  - Confidence: 🟢

- [ ] **T-17 — The picklable worker context.**
  `_WorkerSolveCtx` carrying the `asb.Airplane`, constraints, capabilities,
  `effective_mass_kg` and `_AircraftMassOnly(total_mass_kg)`;
  `_worker_ctx_from(ctx)`; `_solve_target_in_worker`; and
  `_solve_targets_in_parallel` yielding `(target, point | None)` in
  `as_completed` order, converting a worker exception into `(target, None)`
  after logging.
  - Legacy origin: `:1268-1352`
  - Definition of done: **no DB session is reachable from a worker** — assert
    that `_WorkerSolveCtx` pickles and contains no SQLAlchemy object; one
    failing target does not abort the run.
  - Confidence: 🟢

- [ ] **T-18 — The SSE generator.**
  Setup failure ⇒ a single `error` event and return. Then: filter `supported`,
  optionally clear, insert an **empty** point-set row, flush, **commit**, emit
  `targets`; per solved point insert, flush, append the id, **commit**, refresh
  and emit `op`; a `None` point emits `skip`; finish with `done`.
  Headers `Cache-Control: no-cache`, `X-Accel-Buffering: no`.
  - Legacy origin: `:1413-1491`,
    `app/api/v2/endpoints/operating_points.py:126-150`
  - Definition of done: an interruption after three `op` events leaves exactly
    three persisted points and a point set referencing exactly those; an unknown
    UUID produces HTTP 200 with one `error` event.
  - 🔴 **Deviation required (BR-MS39):** capability-gated targets are filtered
    out **before** `targets` is emitted, so they appear in neither `targets` nor
    `skip` and the client cannot tell why they are missing. Emit a `skip` (or a
    `targets` entry with `status: "SKIPPED"`) carrying the missing capability
    and the available controls, and add a `reason` field to `skip`.
  - 🟡 This generator calls `db.commit()` directly, a deliberate exception to
    BR-78 / ADR 0009. Keep it, but document it at the call site.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Reference-speed precedence.** Four cases: full per-config
      context, legacy `v_stall_mps` only, no context, and a context with zeros
      or negatives (treated as absent). Assert the `provenance` in each.
- [ ] **TT-02 — No 0.95/0.90.** A context with `v_s1 = 12` and no per-config
      values yields `vs_to == vs_ldg == 12.0` (regression against the historical
      heuristic).
- [ ] **TT-03 — Floors applied last.** `v_s1 = 1.0` ⇒ `3.0 / 2.5 / 2.0`.
- [ ] **TT-04 — Cold-start stamping.** All fifteen targets carry
      `STALE_NO_POLAR`; the polar path carries none; the input list is not
      mutated.
- [ ] **TT-05 — The fifteen targets.** Golden-file comparison of names, configs,
      velocities, flaps and `n_target` for a known profile + refs pair.
- [ ] **TT-06 — Turn load factors.** 1.0642 / 1.3054 / 2.0.
- [ ] **TT-07 — `V_max` fallback.** No `max_level_speed_mps` ⇒
      `max(1.35·V_c, V_c + 8)`.
- [ ] **TT-08 — `V_md` substitution propagates.** With no profile, *every*
      cruise-derived velocity follows `v_md_mps` — assert on
      `best_angle_climb_vx`, `loiter_endurance` and `max_range`, not only
      `cruise`.
- [ ] **TT-09 — Flap clipping.** Two flaps (25°, 30°) ⇒ a 30° request clips to
      25° with the warning; a 15° request is untouched; no flap TED ⇒ identical
      target; the warning is not duplicated on a second pass.
- [ ] **TT-10 — Capability matrix.** Elevon ⇒ pitch + roll; ruddervator ⇒ pitch
      + yaw; rudder only ⇒ turns generated; no roll and no yaw ⇒ turns and
      dutch-roll skipped, eleven remain; no flap ⇒ only `stall_with_flaps`
      skipped.
- [ ] **TT-11 — Stage 1 is skipped-on-success.** With a mocked solver returning
      a 0.12 score, the grid evaluator is never called.
- [ ] **TT-12 — `Opti` exception is not fatal.** A raising `asb.Opti` still
      produces the point via the fallback, with `trim_method ==
      "grid_fallback"`.
- [ ] **TT-13 — The fallback moves velocity (gh-528 regression).** The persisted
      velocity differs from the target velocity.
- [ ] **TT-14 — Descending ladder for `max_level_speed`.** The candidate
      velocities are `[28.0, 26.6, 25.2, 23.8]` for a 28 m/s target, floored at
      2 m/s for a tiny base.
- [ ] **TT-15 — CL target per candidate velocity.** The fallback recomputes
      `CL_target` at each candidate speed, not once at the original.
- [ ] **TT-16 — Status thresholds.** 0.34 ⇒ TRIMMED; 0.36 ⇒ NOT_TRIMMED +
      warning; α beyond the bound ⇒ LIMIT_REACHED overriding TRIMMED; a `None`
      bound disables the check.
- [ ] **TT-17 — Turn feasibility.** `V < V_s1·√n` ⇒ LIMIT_REACHED with a warning
      **starting with** `STALL_IN_TURN`; a feasible turn is untouched.
- [ ] **TT-18 — `trim_residuals` rejects strings** (gh-627 regression).
- [ ] **TT-19 — Persistence shape.** `xyz_ref == [design_cg_x, 0, 0]` on every
      row; α stored in radians; the set name and description exact; the id list
      matches the inserted rows.
- [ ] **TT-20 — `replace_existing`.** Pin today's aircraft-wide deletion
      (including a manually created point), then flip the assertion when T-14's
      scoping lands.
- [ ] **TT-21 — Batch path stays sequential.** A mocked solver records call
      order equal to target order, and no `ProcessPoolExecutor` is created.
- [ ] **TT-22 — Pool hygiene.** After `_get_opg_executor()`, the parent's five
      BLAS variables have their original values; a worker reports `"1"`;
      concurrent callers create one executor.
- [ ] **TT-23 — Worker isolation.** `_WorkerSolveCtx` pickles; it contains no
      SQLAlchemy instance; a worker cannot import a session (assert on the
      dataclass fields).
- [ ] **TT-24 — One bad target does not kill the run.** A worker that raises
      yields a `skip`; the other fourteen still produce `op` events.
- [ ] **TT-25 — Incremental commit.** Interrupt the generator after three `op`
      events; exactly three rows persist and the point set lists exactly those
      three ids.
- [ ] **TT-26 — Setup failure is an event.** An unknown UUID ⇒ HTTP 200 with a
      single `error` event and no further output.
- [ ] **TT-27 — Capability visibility (post-fix).** A rudderless aircraft's
      `dutch_role_start` appears as a `skip` (or a `SKIPPED` target entry) with
      a reason — currently it appears nowhere.
- [ ] **TT-28 — Enrichment failure is survivable.** A raising
      `compute_enrichment` still yields the point, without
      `trim_enrichment`.
- [ ] **TT-29 — Fast-tier coverage.** Every task above has a test that stubs
      `asb.Opti` and `asb.AeroBuildup` so it runs in the CI fast tier without
      AeroSandbox (ADR 0015); the real-solver tests are marked `slow` and, per
      the memory-pressure rule, run **sequentially**.

## Data Migration Tasks

- [ ] **TM-01 — `operating_points`.** Columns per
      [`../../aero-analysis/contracts.md`](../../aero-analysis/contracts.md);
      `alpha`/`beta` in **radians**; `warnings`, `controls`, `xyz_ref`,
      `trim_enrichment` as JSON; `status` defaulting to `NOT_TRIMMED`.
      🟡 The legacy FK `aircraft_id → aeroplanes.id` has no `ondelete` clause —
      add `ON DELETE CASCADE`.
- [ ] **TM-02 — `operating_pointsets`.** `source_flight_profile_id` referencing
      `rc_flight_profiles`.
      🟡 `operating_points` is a **JSON id list** with no referential
      integrity — consider a real association table with `ON DELETE CASCADE`.

## Suggested Order

1. **T-01 → T-04** are pure functions over dicts — build and test them first,
   with no solver in sight.
2. **T-05** (capabilities) next; it only needs an `asb.Airplane` shape.
3. **T-07** (scoring) before **T-06** and **T-08**, which both consume it.
4. **T-06, T-08** (the two stages) can be built in parallel behind a stubbed
   solver.
5. **T-09, T-10** (status, turns) then **T-11** (orchestration), which composes
   T-06 → T-10.
6. **T-12** (`_prepare_generation`) once T-01…T-05 exist; **T-13** immediately
   after.
7. **T-14, T-15** (persistence, batch path) before any parallelism.
8. **T-16, T-17, T-18** (pool, worker context, stream) last — the streaming path
   is an optimisation over a correct sequential implementation.

Blocking edges: T-03 ⇠ T-01 · T-04 ⇠ T-03 · T-06 ⇠ T-07 · T-08 ⇠ T-07 ·
T-11 ⇠ T-06, T-08, T-09 · T-12 ⇠ T-01…T-05 · T-13 ⇠ T-11, T-12 ·
T-15 ⇠ T-13, T-14 · T-17 ⇠ T-16 · T-18 ⇠ T-15, T-17.

## Pending Gaps (🔴)

- **The grid fallback cannot move a control surface** (T-08). `best_controls`
  is always `{}`. Should the fallback search a coarse deflection grid, or should
  an unreachable target get its own status instead of `NOT_TRIMMED`?
- **Capability-gated targets are invisible on the stream** (T-18). They appear
  in neither `targets` nor `skip`, and `skip` has no reason field. The batch
  path logs a warning the stream client never sees.
- **`replace_existing` deletes manual operating points** (T-14). Scope it, or
  rename it.
- **`STALL_IN_TURN` is a sentence, not a token** (T-10) — the only formatted
  entry in `warnings[]`.
- **`target_turn_n` and `loiter_s` are validated but never used** (T-03). A user
  who sets `target_turn_n = 3.0` sees no change; the banks are hard-coded at
  20/40/60°.
- **`has_pitch_control` is detected but never required** (T-05). Should a
  pitchless aircraft skip everything, or keep generating and trim with nothing?
- **The `Opti` failure log is DEBUG-only** (T-06), so a systematically failing
  stage 1 — and the ~4× slower grid path it implies — is invisible in
  production.
- **The six objective weights are unnamed and unjustified** (T-06).
- **The reference-speed `provenance` is not persisted** (T-02) — only its
  consequence.
- **The point set stores a JSON id list** (TM-02) with no referential integrity.
- **A dead worker is not detected** (T-17); the pool is reused and the target
  yields `None`.
- **The streaming path commits directly** (T-18) — a documented exception to
  ADR 0009 that should be re-affirmed rather than inherited silently.
