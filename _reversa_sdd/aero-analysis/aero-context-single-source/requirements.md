# aero-context-single-source

> Use-case specification, nested under the module
> [`aero-analysis`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: aero-analysis
> (R1–R10, the aero context), `_reversa_sdd/data-dictionary.md`
> §`assumption_computation_context`, `_reversa_sdd/domain.md` BR-14…BR-18,
> ADR 0004, ADR 0012.

## Overview

`aero-context-single-source` is the gh-924 invariant made executable: **one**
pipeline computes `cd0` (parasite), `e_oswald`, `(L/D)max` and `x_np` at the
cruise point and caches them on `aeroplanes.assumption_computation_context`.
Every downstream consumer — speed polar, V-n envelope, matching chart, mission
KPIs, endurance, spar sizing, powertrain, copilot — **reads that context**;
none re-derives its own. The use case also owns the polar fitting, its six
rejection gates, the Oswald provenance chain and the Reynolds-banded polar
table. 🟢

## Responsibilities

- Build the ASB airplane and take the reference geometry from the **largest**
  wing, overriding AeroSandbox's `wings[0]` default. 🟢
- Seed the design assumptions and the computation config idempotently before
  computing anything. 🟢
- Run the stability point at cruise, the coarse α sweep and the fine α×V sweep —
  each as **one** vectorised solver call. 🟢
- Publish `cd0` as **parasite** drag, not total CD. 🟢
- Publish `(L/D)max` and `CL_at_(L/D)max` from the self-consistent closed form,
  not from the sweep argmax. 🟢
- Fit a parabolic polar per configuration through six rejection gates, refining
  only the two refinable ones. 🟢
- Resolve `e_oswald` through the provenance chain
  `aerobuildup_trefftz → fit → fallback`. 🟢
- Write `cg_x = x_np − target_SM · MAC` back as a CALCULATED assumption. 🟢
- Build the Reynolds-banded polar table and backfill its fallback rows with the
  authoritative values. 🟢
- Derive the closed-form V-speeds with one Picard refinement pass and the
  sub-stall clamp. 🟢
- Cache the whole result in one JSON column, with `computed_at` provenance. 🟢

**Explicitly NOT this use case's responsibility:** the design-assumption CRUD,
ESTIMATE/CALCULATED duality and event routing
(→ [`../../mission-and-sizing/design-assumptions/`](../../mission-and-sizing/design-assumptions/requirements.md)),
the V-n envelope, matching chart and field lengths (→ `mission-and-sizing`),
per-airfoil polars (→ `airfoil-catalog`), and CG aggregation from mass items
(→ `mass-and-balance`).

## Business Rules

- **BR-14 — One aero truth per aircraft (gh-924, commit `8847b13d`, ADR 0004).**
  🟢 `cd0` (parasite), `e_oswald`, `(L/D)max` and `x_np` are produced **once**
  by `recompute_assumptions` at the cruise point and cached on
  `assumption_computation_context`. No consumer re-derives them.
  *🟢 **`_auto_populate_cd0` is deleted** (`Q-AA-1`, maintainer-answered) — it wrote *total* CD into the parasite-CD0 assumption, a confirmed BR-14 / ADR 0004 violation that collapsed (L/D)max from ≈24 to ≈17.* Previously it wrote the
  **total** CD into the `cd0` assumption on a different trigger.
- **BR-AA5 — The main wing is `argmax(wing.area())`.** 🟢 `s_ref` / `c_ref` /
  `b_ref` are overridden from the largest wing; AeroSandbox defaults to
  `wings[0]`, which may be a tail — the gh-788/F1 bug class that produced ~8×
  wrong coefficients for tail-first imports.
- **BR-AA6 — CD0 is the parasite drag.** 🟢 (`_parasite_cd0`, `:1098-1112`)

  ```
  CD_induced = CL² / (π · AR · e)      # e = AeroBuildup's own oswalds_efficiency
  CD0        = CD_total − CD_induced   # only when CL/AR/e are sane AND result > 0
  ```

  On a cambered wing α = 0 already carries lift (CL ≈ 0.55 for a glider), so
  publishing `coefficients.CD` as CD0 double-counts induced drag and collapses
  `(L/D)max` — 17 instead of 24 on a high-AR glider. Ratified against
  Anderson §6.7.2.
- **BR-AA7 — `(L/D)max` from the self-consistent scalars.** 🟢 (`:282-300`,
  Scholz eq. 5.39)

  ```
  E_max       = ½ · sqrt(π · AR · e / CD0)
  CL_at_E_max = sqrt(CD0 · π · AR · e)
  ```

  The flattened-sweep `argmax(CL/CD)` mixes Reynolds bands and lands on a
  spurious high-CL sample (eHawk: 18.8 @ CL 0.98 vs the correct 23.4 @ CL 0.55).
  The measured argmax survives only as the fallback when the parabolic scalars
  are unavailable.
- **BR-AA8 — Oswald provenance is a recorded chain.** 🟢
  `aerobuildup_trefftz` → `fit` → `fallback`, stored per configuration in
  `e_oswald_provenance` and mirrored by `context["e_oswald_fallback_used"]`.

  ```
  e   = CL² / (π · AR · CDi)   at the (L/D)max sample
  CDi = D_induced / (q · S_ref)              # collected during the fine sweep
  sanity clip: reject unless 0 < e ≤ 1.10
  e_oswald_effective = e or 0.8
  ```

  `D_induced` comes free with the vectorised fine sweep — **zero** extra
  AeroBuildup calls (gh-636).
- **BR-16 — Resolution goes up; thresholds never move (gh-672).** 🟢 Six
  rejection gates on `CD = CD0 + k·CL²` fitted by OLS over
  `CL ∈ [max(0.10, 0.10·CL_max), 0.85·CL_max]`, `e = 1/(π·AR·k)`:

  | Gate | Accept condition | Category |
  |---|---|---|
  | `insufficient_points` | ≥ 6 samples in the window (also fires on `AR ≤ 0`) | `sweep` |
  | `non_monotonic_polar` | `dCD/d(CL²) ≥ −1e-6` (laminar-bubble / stall guard) | `data` |
  | `negative_slope_k` | `k > 0` | `design` |
  | `non_positive_cd0` | `cd0_fit > 0` | `consistency` |
  | `unphysical_e_oswald` | `0.4 < e ≤ 1.0` | `design` |
  | `cd0_stability_mismatch` | `\|cd0_fit − cd0_stability\| / cd0_stability ≤ 0.20` | `consistency` |

  Refinement retries **only** `_REFINABLE_REJECTION_GATES =
  {insufficient_points, non_monotonic_polar}`, halving the α step and
  multiplying the margin by 1.5 per attempt (max 2), setting `auto_refined=True`
  only when a refinement actually produced a fit.
- **BR-17 — An unphysical result is a design warning, not a fallback
  (gh-956, ADR 0012).** 🟢 `PolarRejection` enforces the canonical gate→category
  pair with a model validator, and **only `category == "design"`** reaches the
  user. A `k ≤ 0` or an out-of-range `e` becomes a visible design warning, never
  a silent `0.8`.
- **BR-18 — Turbulator deltas never poison the fit gate (gh-935).** 🟢 The
  stored `cd0` gains `+ ΔCD0` (`apply_turbulator_delta_to_cd0`, `:2099-2168`;
  area-weighted, ×2 for a symmetric wing), but `raw_cd0` is preserved and passed
  as `cd0_stability` to every fit — otherwise a meaningful ΔCD0 would trip the
  20 % consistency gate.
- **BR-AA9 — Sweeps are vectorised (gh-690).** 🟢 One `AeroBuildup.run()` each
  for the coarse sweep, the fine sweep and the lift-curve extraction (was ~150
  calls per polar config). The fine grid is
  `np.meshgrid(alphas, velocities, indexing="xy")` — **V-outer / α-inner** ravel
  order, which downstream consumers index against.
  `v_stall_approx = max(0.5·V_cruise, 3.0)`;
  `velocities = linspace(v_stall_approx, v_max, fine_velocity_count)`;
  `alphas = arange(stall_α ± margin, step)`.
- **BR-AA10 — The lift curve has a hard quality gate (gh-487/gh-871).** 🟢
  `CL = CL_α·α + CL_0` by least squares over α ∈ [−2°, +6°]; returns
  `(None, None)` when `R² < 0.995`, when `CL_α ≤ 0`, or when fewer than 3 finite
  points survive. `α₀ = degrees(−CL_0 / CL_α)`.
- **BR-AA11 — Picard refinement is exactly one pass (gh-493 A7).** 🟢 Look up
  `cd0`/`e` at the scalar `V₀` in `polar_re_table`, re-solve, accept `V₁`, log a
  warning when `|ΔV|/V₀ ≥ 5 %`. Applied to `V_md`, `V_min_sink`, `V_max`.
- **BR-AA12 — Sub-stall clamp (gh-683).** 🟢 `V_md` and `V_min_sink` are clamped
  to `max(V, V_stall)`; the closed-form optimum CL can exceed `CL_max` on
  high-AR / draggy polars and back-solve a physically unreachable speed.
- **BR-AA13 — Re-table fallback rows are backfilled (gh-924).** 🟢 A rejected
  band's `cd0`/`e` are `None` and the lookups would fall back to a hard-coded
  `0.03 / 0.8` contradicting the cruise values. Every row with
  `fallback_used or cd0 is None` is overwritten with the single-source parasite
  `cd0` and the Trefftz `e` (`:444-449`).
- **BR-CX1 — The pipeline is layered, and a fatal failure writes nothing.** 🟢
  - *fatal* — an AeroBuildup failure in the stability run, the coarse sweep or
    the fine sweep logs and **returns**, leaving the previous context valid;
  - *degraded* — each per-configuration polar sits in its own `try` (a takeoff
    failure must not block the physically independent landing pass) and falls
    back to a clone of the clean polar with `provenance="aerobuildup_failed"`;
    the Re-table, the turbulator ΔCD0 and the elevator-authority forward-CG
    limit are non-fatal with named fallbacks;
  - *guarded* — a schema/ASB **flap-name parity mismatch** routes to the no-flap
    fallback with an explicit "investigate the converter" warning instead of an
    `AssertionError` on the live path (gh-537).
- **BR-CX2 — The pipeline is synchronous.** 🟢 `recompute_assumptions` is a
  **sync** function; async callers must wrap it in `asyncio.to_thread`.
- **BR-CX3 — Seeding is idempotent and unconditional.** 🟢 `seed_defaults()` and
  `_load_or_create_config()` run on **every** recompute, because wings can be
  created before the user ever opens the Assumptions tab.
- **BR-CX4 — An aircraft without wings is skipped silently.** 🟢 Step 0 returns
  without writing and without raising.
- **BR-83 — Recompute triggers exclude the recompute's own outputs.** 🟢
  `AssumptionChanged` schedules a recompute only for
  `_RECOMPUTE_TRIGGERING_PARAMS = {target_static_margin, mass}`. `cg_x`, `cd0`
  and `cl_max` are deliberately excluded to break the
  `recompute → AssumptionChanged(cg_x) → recompute` loop.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Take reference geometry from the largest wing | Must | A tail-first import produces the same `s_ref` as a wing-first one |
| RF-02 | Seed assumptions and computation config idempotently on every run | Must | A second recompute creates no duplicate rows |
| RF-03 | Run the stability point, the coarse sweep and the fine sweep in one solver call each | Must | Three `AeroBuildup.run()` calls per configuration, not ~150 |
| RF-04 | Publish `cd0` as parasite drag | Must | Cambered wing: `context.cd0 < CD_total` |
| RF-05 | Publish `(L/D)max` from the closed form | Must | `ld_max == 0.5·sqrt(π·AR·e/CD0)` when the scalars exist |
| RF-06 | Fit a parabolic polar per configuration with six gates | Must | Each gate fires on a crafted polar; the categories match the canonical table |
| RF-07 | Refine only `insufficient_points` and `non_monotonic_polar` | Must | `negative_slope_k` is never retried; thresholds never move |
| RF-08 | Surface only `design`-category rejections | Must | `cd0_stability_mismatch` stays internal; `unphysical_e_oswald` is shown |
| RF-09 | Resolve `e_oswald` through the provenance chain with a sanity clip | Must | `e = 1.3` is rejected; `e_oswald_provenance` is always populated |
| RF-10 | Extract `CL_α` and `α₀` with an `R² ≥ 0.995` gate | Must | A poor fit yields `(None, None)`, never a low-quality slope |
| RF-11 | Write `cg_x = x_np − target_SM · MAC` as a CALCULATED value | Must | Changing `target_static_margin` moves `cg_x` on the next recompute |
| RF-12 | Add turbulator ΔCD0 to the stored `cd0` while gating on `raw_cd0` | Must | A meaningful ΔCD0 does not trip the 20 % consistency gate |
| RF-13 | Build the Re-banded polar table from existing samples | Must | No extra solver calls; ≤ ~200 ms for three OLS fits |
| RF-14 | Backfill fallback rows with the authoritative `cd0`/`e` | Must | No row reports `0.03 / 0.8` while the context holds different values |
| RF-15 | Derive the closed-form V-speeds | Must | `V_ms ≈ 0.760 · V_md` on a clean polar |
| RF-16 | Apply exactly one Picard pass to `V_md`, `V_min_sink`, `V_max` | Must | The lookup runs once; `\|ΔV\|/V₀ ≥ 5 %` logs a warning |
| RF-17 | Clamp `V_md` and `V_min_sink` to `max(V, V_stall)` | Must | A draggy high-AR polar cannot produce a sub-stall best-glide speed |
| RF-18 | Cache the whole result in one JSON column with `computed_at` | Must | `GET …/assumptions/computation-context` returns every documented key |
| RF-19 | Leave the previous context intact on a fatal failure | Must | A stability-run exception does not clear or corrupt the cache |
| RF-20 | Keep per-configuration polars independent | Must | A takeoff failure still yields a landing polar |
| RF-21 | Route a flap-name parity mismatch to the no-flap fallback with a warning | Must | No `AssertionError` reaches the live path (gh-537) |
| RF-22 | Skip an aircraft with no wings silently | Should | No context is written and no error is raised |
| RF-23 | Expose a manual recompute trigger and a job-status read | Should | `POST …/recompute` → 202; `GET …/assumptions/recompute-status` → state |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Performance | Sweeps are vectorised: ~150 solver calls collapsed to 1 per sweep | gh-690 (`803b0236`) | 🟢 |
| Performance | The Oswald factor reuses `D_induced` already collected by the fine sweep — zero extra calls | `_e_oswald_from_sweep` (gh-636) | 🟢 |
| Performance | The Re-table re-bins existing samples; marginal cost ≤ 200 ms for three OLS fits | `polar_re_table_service` (gh-493) | 🟢 |
| Performance | Recompute is debounced (`debounce_seconds = 2.0`) before it runs | `aircraft_computation_config` | 🟢 |
| Correctness | Reference geometry comes from the largest wing, never `wings[0]` | recompute step 1 (gh-788) | 🟢 |
| Correctness | `cd0` has exactly one intended writer | ADR 0004 | 🟢 (🔴 violated by `_auto_populate_cd0`) |
| Correctness | The recompute trigger set excludes the recompute's own outputs, breaking the feedback loop | `_RECOMPUTE_TRIGGERING_PARAMS` (BR-83) | 🟢 |
| Robustness | A fatal failure leaves the previous context valid instead of writing a partial one | recompute error policy | 🟢 |
| Robustness | Each per-configuration polar is independently guarded | same | 🟢 |
| Robustness | The flap-parity guard converts an `AssertionError` into a warned fallback | gh-537 | 🟢 |
| Auditability | `e_oswald_provenance`, `e_oswald_fallback_used`, `auto_refined`, `computed_at` make the numbers traceable | `ParabolicPolar`, context keys | 🟢 |
| Concurrency | The pipeline is sync; async callers must offload it to a thread | `asyncio.to_thread` requirement | 🟢 |

## Acceptance Criteria

```gherkin
Feature: One aero truth

  Scenario: Parasite CD0, not total CD
    Given a cambered wing whose CL at alpha 0 is 0.55
    When recompute_assumptions runs at the cruise point
    Then context cd0 equals CD_total minus CL^2 / (pi * AR * e)
    And context cd0 is strictly less than the analysis CD

  Scenario: L over D max from the closed form
    Given a parabolic polar with CD0 0.021, AR 14 and e 0.86
    When the context is published
    Then ld_max equals 0.5 * sqrt(pi * 14 * 0.86 / 0.021)
    And it is not the argmax of CL/CD over the raw sweep

  Scenario: Reference geometry comes from the largest wing
    Given an aircraft whose wings list starts with the horizontal tail
    When the context is computed
    Then s_ref, c_ref and b_ref describe the main wing
    And the coefficients are not scaled by the tail-to-wing area ratio

Feature: Polar fitting

  Scenario: An unphysical Oswald factor is a design warning
    Given a fit whose e evaluates to 1.4
    When the fit is evaluated
    Then the rejection gate is "unphysical_e_oswald" with category "design"
    And it is surfaced to the user
    And cd0 and e_oswald on that polar are null

  Scenario: A consistency rejection stays internal
    Given a fit whose cd0 differs from the stability cd0 by 35 percent
    Then the gate is "cd0_stability_mismatch" with category "consistency"
    And it is not surfaced to the user

  Scenario: Refinement raises resolution only
    Given a fit rejected with gate "insufficient_points"
    When the refinement runs
    Then the alpha step is halved and the margin multiplied by 1.5
    And at most two attempts are made
    And no gate threshold changes
    And auto_refined is true only if a fit was produced

  Scenario: A design rejection is never retried
    Given a fit rejected with gate "negative_slope_k"
    Then no refinement attempt is made

  Scenario: A turbulator delta does not trip the consistency gate
    Given a turbulator that adds 0.004 to cd0
    When the polars are fitted
    Then the fit is gated against raw_cd0, not against the adjusted cd0
    And cd0_stability_mismatch does not fire

Feature: Oswald provenance

  Scenario: Trefftz is preferred
    Given AeroBuildup reports an Oswald efficiency of 0.86
    Then e_oswald is 0.86 and e_oswald_provenance is "aerobuildup_trefftz"

  Scenario: An out-of-range value is rejected
    Given a swept-derived e of 1.3
    Then it is rejected by the 0 < e <= 1.10 clip
    And the provenance falls through to "fit" or "fallback"

Feature: Speeds

  Scenario: Minimum sink is 3^(-1/4) of minimum drag speed
    Given a valid parabolic polar
    Then v_min_sink_mps is approximately 0.760 times v_md_mps

  Scenario: A sub-stall optimum is clamped
    Given a high aspect-ratio draggy polar whose optimum CL exceeds CL_max
    When the speeds are derived
    Then v_md_mps is at least v_stall_mps

  Scenario: Picard runs exactly once
    Given a Reynolds-banded table
    When v_md is refined
    Then the table is consulted once
    And a warning is logged if the speed moved by 5 percent or more

Feature: Error policy

  Scenario: A fatal failure preserves the previous context
    Given a cached context from an earlier run
    When the cruise stability run raises
    Then nothing is written
    And the earlier context is still readable

  Scenario: A takeoff-polar failure does not block landing
    Given the takeoff configuration solve raises
    When the recompute continues
    Then the takeoff polar is a clone of the clean polar with provenance "aerobuildup_failed"
    And the landing polar is computed normally

  Scenario: A flap-name parity mismatch is warned, not asserted
    Given the model reports a flap TED but the ASB conversion produced no flap-role surface
    When the polars are computed
    Then the no-flap fallback is used
    And a warning tells the operator to investigate the converter

  Scenario: An aircraft without wings is skipped
    Given an aeroplane with no wings
    When recompute_assumptions runs
    Then no context is written
    And no exception is raised
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Parasite CD0 (RF-04) | Must | The defining gh-924 fix; wrong by ~2× on a cambered wing and it corrupts nine consumers at once |
| `(L/D)max` closed form (RF-05) | Must | A 30 % error otherwise, with no visible symptom |
| Largest-wing reference geometry (RF-01) | Must | ~8× wrong coefficients on tail-first imports (gh-788/F1) |
| Six gates + category routing (RF-06…RF-08) | Must | The only mechanism that stops a bad fit from becoming an authoritative number |
| Oswald provenance chain (RF-09) | Must | Determines induced drag everywhere downstream |
| Context caching (RF-18) | Must | The contract itself — every consumer reads it |
| Fatal/degraded/guarded error policy (RF-19…RF-21) | Must | A partial context is worse than a stale one |
| Vectorised sweeps (RF-03) | Must | The difference between a 2 s and a 5 min recompute |
| Re-table + backfill (RF-13, RF-14) | Must | Without the backfill the Re-lookups contradict the cruise values |
| V-speeds + Picard + clamp (RF-15…RF-17) | Must | Feed OP generation, V-n, matching chart and the KPIs |
| `cg_x` write-back (RF-11) | Must | BR-28: CG is a top-down design target |
| Turbulator ΔCD0 (RF-12) | Should | Only relevant with a turbulator configured |
| Manual recompute trigger + status (RF-23) | Should | Convenience over the automatic debounced path |
| No-wing skip (RF-22) | Should | A cold-start convenience |
| Removing `_auto_populate_cd0` | **Must (open)** | Confirmed BR-14 violation from `stability-derivatives` |
| Translating the German `hint` strings | Should (open) | English-only UI |
| Re-deriving `cd0`/`e` in any consumer | Won't | Forbidden by BR-14 / ADR 0004 |
| Running AVL anywhere in this pipeline | Won't | Hard-coded AeroBuildup (ADR 0003) |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/assumption_compute_service.py` | `recompute_assumptions` (`:59-809`), `_parasite_cd0` (`:1098-1112`), `(L/D)max` block (`:282-300`), `_fit_parabolic_polar` (`:1417-1610`), `_fit_parabolic_polar_with_refinement` (`:1618-1694`), `_e_oswald_from_sweep`, `_coarse_alpha_sweep`, `_fine_sweep_cl_max`, `_extract_cl_alpha_from_linear_sweep` (`:1219`), `_picard_iterate_speed` (`:2033`), `apply_turbulator_delta_to_cd0` (`:2099-2168`), `_cache_context`, Re-table backfill (`:444-449`) | 🟢 |
| `app/services/polar_re_table_service.py` | `build_re_table`, `lookup_cd0_at_v`, `lookup_e_oswald_at_v` | 🟢 |
| `app/schemas/polar_by_config.py` | `ParabolicPolar`, `PolarRejection` + the gate→category model validator | 🟢 |
| `app/schemas/polar_re_table.py` | `PolarReTableRow` (`:18`) | 🟢 |
| `app/models/computation_config.py` | `AircraftComputationConfigModel`, `COMPUTATION_CONFIG_DEFAULTS` (`:8-16`) | 🟢 |
| `app/api/v2/endpoints/aeroplane/design_assumptions.py` | `GET …/assumptions/computation-context`, `POST …/recompute`, `GET …/assumptions/recompute-status` | 🟢 |
| `app/services/invalidation_service.py` | `_RECOMPUTE_TRIGGERING_PARAMS` (BR-83) | 🟢 |
| dead code | `_load_cg_agg` (`:1739`), `_extract_scalar` (`:1316`, tests only) | 🔴 |
