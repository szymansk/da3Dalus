# aero-context-single-source — Implementation Tasks

> Executable sequence to re-implement this use case from the legacy behaviour.
> Every task cites the legacy file, a definition of done, and a confidence
> marker. Parent module tasks: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] `analyse_aerodynamics` + `AnalysisModel`
      ([`../tasks.md`](../tasks.md) T-01, T-02).
- [ ] AeroSandbox ≥ 4.0.7 with `AeroBuildup.run()` accepting an array-shaped
      `OperatingPoint` and exposing `oswalds_efficiency` and `D_induced`.
- [ ] Design assumptions seeded (`seed_defaults`) and
      `aircraft_computation_config` present
      (→ [`../../mission-and-sizing/design-assumptions/tasks.md`](../../mission-and-sizing/design-assumptions/tasks.md)).
- [ ] `aeroplanes.assumption_computation_context` JSON column.
- [ ] The debounced job tracker (`schedule_recompute_assumptions`).
- [ ] A flight-profile loader (`_load_effective_flight_profile`).

## Tasks

- [ ] **T-01 — Reference geometry from the largest wing.**
  `main_wing = argmax(wing.area())`; override `s_ref`, `c_ref`, `b_ref` from it
  before any solver call.
  - Legacy origin: `app/services/assumption_compute_service.py` step 1 (gh-788)
  - Definition of done: an aircraft whose `wings[0]` is the horizontal tail
    produces the same reference geometry as the same aircraft with the main wing
    first; coefficients do not scale by the tail-to-wing area ratio.
  - Confidence: 🟢

- [ ] **T-02 — Unconditional idempotent seeding.**
  Call `seed_defaults()` and `_load_or_create_config()` on **every** recompute.
  - Legacy origin: same, step 2
  - Definition of done: a second recompute creates no duplicate assumption or
    config rows; a wing created before the Assumptions tab was ever opened still
    gets a complete parameter set.
  - Confidence: 🟢

- [ ] **T-03 — The three vectorised solver calls.**
  `_stability_run_at_cruise`, `_coarse_alpha_sweep` (→ `stall_α = argmax(CL)`)
  and `_fine_sweep_cl_max`, each issuing **one** `AeroBuildup.run()`. Build the
  fine grid as `np.meshgrid(alphas, velocities, indexing="xy")` — V-outer /
  α-inner. `v_stall_approx = max(0.5·V_cruise, 3.0)`;
  `velocities = linspace(v_stall_approx, v_max, fine_velocity_count)`;
  `alphas = arange(stall_α ± margin, step)`. Collect `cl[]`, `cd[]`, `v[]` and
  `cdi[]` — `D_induced` must be captured here so the Oswald factor costs nothing
  extra (gh-636).
  - Legacy origin: `app/services/assumption_compute_service.py` steps 3–5 (gh-690)
  - Definition of done: a mocked `AeroBuildup.run` records exactly three calls
    per configuration; the ravel order matches what T-05 and T-09 index against.
  - Confidence: 🟢

- [ ] **T-04 — Parasite CD0.**

  ```
  CD_induced = CL² / (π · AR · e)
  CD0        = CD_total − CD_induced
  guard: CL, AR, e finite and positive AND CD0 > 0, else None
  ```

  - Legacy origin: `app/services/assumption_compute_service.py:1098-1112`
  - Definition of done: a cambered wing with CL(α=0) = 0.55 yields
    `cd0 < CD_total`; a symmetric wing at CL ≈ 0 converges to `CD_total`;
    a nonsensical `e` yields `None` rather than a negative CD0.
  - Confidence: 🟢

- [ ] **T-05 — `(L/D)max` from the closed form.**
  `E_max = ½·sqrt(π·AR·e/CD0)`, `CL_at_E_max = sqrt(CD0·π·AR·e)`. Keep the
  measured `argmax(CL/CD)` **only** as the fallback when the scalars are absent.
  - Legacy origin: `app/services/assumption_compute_service.py:282-300`
  - Definition of done: the eHawk regression reports ≈ 23.4 @ CL 0.55, not 18.8
    @ CL 0.98; removing `cd0` from the inputs falls back to the measured argmax.
  - Confidence: 🟢

- [ ] **T-06 — `ParabolicPolar` and `PolarRejection`.**
  Schema fields per [`../../data-dictionary.md`](../../data-dictionary.md)
  §`ParabolicPolar`. Enforce the canonical gate→category pairs with a **model
  validator** so a rejection cannot be mis-categorised into visibility.
  - Legacy origin: `app/schemas/polar_by_config.py`
  - Definition of done: constructing a `PolarRejection(gate="negative_slope_k",
    category="sweep")` fails validation; `cd0`/`e_oswald` are `None` exactly
    when a rejection is present.
  - Confidence: 🟢

- [ ] **T-07 — `_fit_parabolic_polar` with six gates.**
  OLS `CD = CD0 + k·CL²` over `CL ∈ [max(0.10, 0.10·CL_max), 0.85·CL_max]`,
  `e = 1/(π·AR·k)`; the six gates exactly as tabulated in
  [`requirements.md`](requirements.md) BR-16.
  - Legacy origin: `app/services/assumption_compute_service.py:1417-1610, :1461-1468`
  - Definition of done: each gate fires on a purpose-built polar; `AR ≤ 0` fires
    `insufficient_points`; the `dCD/d(CL²) ≥ −1e-6` guard catches a laminar
    bubble; no gate threshold is reachable from configuration.
  - Confidence: 🟢

- [ ] **T-08 — Refinement of the two refinable gates only.**
  `_REFINABLE_REJECTION_GATES = {insufficient_points, non_monotonic_polar}`;
  per attempt halve the α step and multiply the margin by 1.5; max 2 attempts;
  `auto_refined = True` only when an attempt produced a fit.
  - Legacy origin: `app/services/assumption_compute_service.py:1618-1694` (gh-672)
  - Definition of done: a `negative_slope_k` rejection triggers **zero**
    refinement attempts; a suite-wide assertion proves no threshold constant is
    mutated during refinement.
  - Confidence: 🟢

- [ ] **T-09 — The Oswald provenance chain.**
  Prefer AeroBuildup's Trefftz `oswalds_efficiency`; else the fit's
  `1/(π·AR·k)`; else `0.8`. Also implement `_e_oswald_from_sweep`:
  `e = CL²/(π·AR·CDi)` at the `(L/D)max` sample with
  `CDi = D_induced/(q·S_ref)` taken from T-03's collected arrays. Clip to
  `0 < e ≤ 1.10`. Record `e_oswald_provenance` per configuration and
  `e_oswald_fallback_used` at context level.
  - Legacy origin: `app/services/assumption_compute_service.py:1412`,
    `_e_oswald_from_sweep` (gh-636)
  - Definition of done: **no** additional `AeroBuildup.run()` is issued to obtain
    `e` (assert the call count is unchanged from T-03); `e = 1.3` is rejected;
    the provenance value is present on every polar.
  - Confidence: 🟢

- [ ] **T-10 — Lift-curve extraction with the quality gate.**
  `CL = CL_α·α + CL_0` by least squares over α ∈ [−2°, +6°]; return
  `(None, None)` when `R² < 0.995`, `CL_α ≤ 0`, or fewer than 3 finite points;
  `α₀ = degrees(−CL_0/CL_α)`.
  - Legacy origin: `app/services/assumption_compute_service.py:1219`
  - Definition of done: a noisy sweep yields `(None, None)` rather than a
    low-quality slope; consumers can therefore fall back to Helmbold-Diederich.
  - Confidence: 🟢

- [ ] **T-11 — `cg_x` write-back.**
  `cg_x = x_np − target_static_margin · MAC`, written as the CALCULATED value
  (BR-28: CG is a top-down design target).
  - Legacy origin: `app/services/assumption_compute_service.py` step 6
  - Definition of done: changing `target_static_margin` moves `cg_x` on the next
    recompute; the aggregated CG from mass items is **never** written into
    `cg_x`.
  - Confidence: 🟢

- [ ] **T-12 — Turbulator ΔCD0 without poisoning the gate.**
  `apply_turbulator_delta_to_cd0`: area-weighted ΔCD0, ×2 for a symmetric wing,
  added to the stored `cd0`; **preserve `raw_cd0`** and pass it as
  `cd0_stability` into every fit.
  - Legacy origin: `app/services/assumption_compute_service.py:2099-2168` (gh-935)
  - Definition of done: a turbulator adding 0.004 to `cd0` does not trip
    `cd0_stability_mismatch`.
  - Confidence: 🟢

- [ ] **T-13 — Per-configuration polars, independently guarded.**
  `{clean, takeoff, landing}`, each in its own `try`. A failure falls back to a
  clone of the clean polar with `provenance = "aerobuildup_failed"`. Flap
  deflection: `0` clean, `min(15, TED)` takeoff, full TED landing.
  - Legacy origin: `app/services/assumption_compute_service.py` step 9
  - Definition of done: a takeoff failure still yields a real landing polar;
    the fallback is labelled and never presented as a measured result.
  - Confidence: 🟢

- [ ] **T-14 — The flap-parity guard (gh-537).**
  When the model reports a flap-role TED but the ASB conversion produced no
  flap-role control surface, route to the no-flap fallback with an explicit
  "investigate the converter" warning instead of letting
  `_run_polar_for_deflection` raise `AssertionError`.
  - Legacy origin: same, error policy "guarded"
  - Definition of done: the mismatch produces a warned fallback, never a 500.
  - Confidence: 🟢

- [ ] **T-15 — The Reynolds-banded polar table (gh-493).**

  ```
  Re_aircraft = ρ·V·MAC_main/μ        (ISA SL, μ = 1.81e-5) — a LABEL, not an ASB parameter
  anchors = [max(0.5·V_cruise, 3.0), V_cruise,
             min(max(1.3·V_cruise, V_max), V_sweep_max)]
  bands   = midpoints between anchors; edges extended by 50 % of the adjacent gap
  degeneracy: Re_max/Re_min < 2.5 → single-row fallback, degenerate = True
  per band: ≥ 6 samples, else a fallback row
  lookup cd0: LINEAR IN 1/sqrt(Re)   (Blasius/Schlichting, cf ∝ Re^(−1/2))
  lookup e  : constant MEAN over non-fallback rows; extrapolation clamps + warns
  ```

  - Legacy origin: `app/services/polar_re_table_service.py:46-59`
  - Definition of done: **no** extra `AeroBuildup.run()`; the table is built by
    re-binning T-03's samples; three OLS fits complete in ≤ ~200 ms.
  - Confidence: 🟢

- [ ] **T-16 — Re-table backfill (gh-924).**
  Overwrite every row with `fallback_used or cd0 is None` using the
  single-source parasite `cd0` and the Trefftz `e`.
  - Legacy origin: `app/services/assumption_compute_service.py:444-449`
  - Definition of done: no lookup can return `0.03 / 0.8` while the context holds
    different authoritative values.
  - Confidence: 🟢

- [ ] **T-17 — Closed-form V-speeds, Picard, clamp, read-back.**
  Implement the whole speed block from [`../design.md`](../design.md) §A6.
  `_picard_iterate_speed` performs **one** pass for `V_md`, `V_min_sink`,
  `V_max`, warning at `|ΔV|/V₀ ≥ 5 %`. Clamp `V_md` and `V_min_sink` to
  `max(V, V_stall)` (gh-683). Read `V_x`/`V_y` back from the
  `best_angle_climb_vx` / `best_rate_climb_vy` OP rows, leaving them `None`
  before generation. `is_glider = (P/W ≤ 0)`.
  - Legacy origin: `app/services/assumption_compute_service.py:2033` + the speed block
  - Definition of done: `V_ms ≈ 0.760·V_md`; a draggy high-AR polar cannot
    produce `V_md < V_stall`; the Picard loop consults the table exactly once per
    speed.
  - Confidence: 🟢

- [ ] **T-18 — Cruise-speed auto-substitution.**
  With no assigned flight profile, `user_set_cruise = False` ⇒ replace the
  cruise speed with `V_md` (best L/D = best range for a prop aircraft) and set
  `v_cruise_auto = True`.
  - Legacy origin: `_load_flight_profile_speeds` +
    `_resolve_cruise_speed_with_md_fallback`
  - Definition of done: an aircraft with no profile reports `v_cruise_auto` true
    and `v_cruise_mps == v_md_mps`; assigning a profile with an explicit cruise
    speed flips it to false.
  - Confidence: 🟢

- [ ] **T-19 — `_cache_context` — the single writer.**
  Assemble every key group from [`design.md`](design.md) §Internal State and
  write the JSON column once, with `computed_at` in ISO-8601 UTC.
  - Legacy origin: `app/services/assumption_compute_service.py` step 12
  - Definition of done: `_cache_context` is the only function that assigns to
    `aeroplanes.assumption_computation_context`; every documented key is present
    (or explicitly `None`).
  - 🟡 **Deviation recommended:** add a `context_schema_version` key so a future
    rename is detectable instead of silently yielding `None` in every consumer.
  - Confidence: 🟢

- [ ] **T-20 — The three-layer error policy.**
  *fatal* → log and return **without writing**; *degraded* → per-configuration
  `try` with a named fallback; *guarded* → the flap-parity route of T-14.
  Demote the cold-start `ValueError` mentioning `x_np=None` / `mac=None` to INFO
  (gh-685).
  - Legacy origin: `app/services/assumption_compute_service.py` error policy
  - Definition of done: a stability-run exception leaves the previous context
    byte-identical; a first-ever recompute logs INFO, not ERROR.
  - Confidence: 🟢

- [ ] **T-21 — Skip an aircraft with no wings.**
  - Legacy origin: same, step 0
  - Definition of done: no context is written, no exception is raised, and the
    caller sees a successful no-op.
  - Confidence: 🟢

- [ ] **T-22 — Recompute triggering and debounce.**
  `AssumptionChanged` schedules a recompute **only** for
  `_RECOMPUTE_TRIGGERING_PARAMS = {target_static_margin, mass}`; `cg_x`, `cd0`
  and `cl_max` are excluded because they are the recompute's own outputs
  (BR-83). Debounce with `aircraft_computation_config.debounce_seconds`
  (default 2.0).
  - Legacy origin: `app/services/invalidation_service.py`
  - Definition of done: writing `cg_x` does not schedule a recompute; a burst of
    edits within the debounce window schedules one run.
  - Confidence: 🟢

- [ ] **T-23 — The read/trigger routes.**
  `GET /aeroplanes/{id}/assumptions/computation-context` → the cached dict (or
  `null`), `POST /aeroplanes/{id}/recompute` → **202** with the job state, and
  `GET /aeroplanes/{id}/assumptions/recompute-status`.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/design_assumptions.py:168-260`
  - Definition of done: the trigger returns 202 (accepted, not completed); the
    status route reflects queued / running / done.
  - Confidence: 🟢

- [ ] **T-24 — Translate the rejection hints.**
  - Legacy origin: `PolarRejection.hint` strings
  - Definition of done: no German text reaches the API surface; the UI is
    English-only.
  - Confidence: 🟡 (a documented deviation from the legacy)

## Test Tasks

- [ ] **TT-01 — Largest-wing reference.** Tail-first and wing-first orderings
      produce identical `s_ref/c_ref/b_ref`.
- [ ] **TT-02 — Idempotent seeding.** Two recomputes, no duplicate rows.
- [ ] **TT-03 — Solver-call budget.** Exactly three `AeroBuildup.run()` calls per
      configuration; obtaining `e` adds none.
- [ ] **TT-04 — Parasite CD0.** Cambered wing → `cd0 < CD_total`; symmetric wing
      at CL ≈ 0 → convergence; bad `e` → `None`.
- [ ] **TT-05 — `(L/D)max` closed form** and its argmax fallback.
- [ ] **TT-06 — Gate→category validator.** A mismatched pair fails construction.
- [ ] **TT-07 — Each of the six gates** fires on a purpose-built polar.
- [ ] **TT-08 — Refinement scope.** `negative_slope_k` → zero attempts;
      `insufficient_points` → step halved, margin ×1.5, ≤ 2 attempts;
      `auto_refined` only on success.
- [ ] **TT-09 — Threshold immutability.** A suite-wide assertion that no gate
      constant changes during any refinement.
- [ ] **TT-10 — Oswald clip and provenance.** `e = 1.3` rejected; provenance
      present on every polar; `e_oswald_fallback_used` set only when 0.8 is used.
- [ ] **TT-11 — Lift-curve gate.** `R² = 0.99` → `(None, None)`;
      `R² = 0.996` → a slope and `α₀`.
- [ ] **TT-12 — `cg_x` write-back** moves with `target_static_margin`.
- [ ] **TT-13 — Turbulator ΔCD0** does not trip the 20 % gate.
- [ ] **TT-14 — Independent polars.** Takeoff failure → labelled fallback;
      landing polar still real.
- [ ] **TT-15 — Flap-parity guard** produces a warned fallback, not
      `AssertionError`.
- [ ] **TT-16 — Re-table construction.** No extra solver calls; degeneracy at
      `Re_max/Re_min < 2.5`; `cd0` interpolation linear in `1/sqrt(Re)`.
- [ ] **TT-17 — Backfill.** No row reports `0.03/0.8` against a different
      context.
- [ ] **TT-18 — Speeds.** `V_ms ≈ 0.760·V_md`; sub-stall clamp; one Picard pass;
      `V_x`/`V_y` `None` before OP generation.
- [ ] **TT-19 — Cruise auto-substitution.** No profile → `v_cruise_auto` true and
      `v_cruise_mps == v_md_mps`.
- [ ] **TT-20 — Fatal policy.** A stability-run exception leaves the previous
      context byte-identical.
- [ ] **TT-21 — Cold start** logs INFO, not ERROR (gh-685).
- [ ] **TT-22 — No wings** → silent skip.
- [ ] **TT-23 — Trigger set.** Writing `cg_x` schedules no recompute; writing
      `mass` does.
- [ ] **TT-24 — Context completeness.** Every documented key is present after a
      successful run.
- [ ] **TT-25 — Fast-tier coverage.** All of the above run **without**
      AeroSandbox by stubbing the sweep functions to return canned arrays
      (ADR 0015 — otherwise this entire pipeline is uncovered against the 80 %
      new-code gate).

## Suggested Order

1. **T-01, T-02** — the pipeline preamble; everything else assumes correct
   reference geometry and seeded parameters.
2. **T-03** — the sweeps, because every later number is derived from their
   arrays (including `cdi[]`, which T-09 needs).
3. **T-04, T-05** — the two headline scalars; both are pure functions over T-03's
   output and can be tested with canned arrays.
4. **T-06 → T-09** — the fit machinery, in that order: schema, gates,
   refinement, provenance. T-06 must precede T-07 so rejections are
   representable.
5. **T-10 → T-14** — the remaining per-configuration work.
6. **T-15, T-16** — the Re-table, which consumes T-03's samples and T-04/T-09's
   authoritative values.
7. **T-17, T-18** — speeds, which consume the Re-table (Picard).
8. **T-19 → T-21** — assembly, error policy and the no-wing guard.
9. **T-22, T-23** — triggering and transport.
10. **T-24** any time.

Blocking edges: T-03 ⇠ T-01 · T-04, T-05 ⇠ T-03 · T-07 ⇠ T-06 · T-08 ⇠ T-07 ·
T-09 ⇠ T-03, T-07 · T-12 ⇠ T-07 · T-15 ⇠ T-03 · T-16 ⇠ T-04, T-09, T-15 ·
T-17 ⇠ T-15 · T-19 ⇠ everything · T-23 ⇠ T-19.

## Pending Gaps

- **`_auto_populate_cd0` must be removed** (owned by
  [`../stability-derivatives/tasks.md`](../stability-derivatives/tasks.md) T-08).
  Until it is, this use case's central guarantee is intermittently false.
- **German `hint` strings (T-24).** Translate — but who owns the wording? The
  hints are the only user-facing explanation of a design-category rejection.
- **No context schema version (T-19).** A key rename silently yields `None` in
  every consumer. Should the context be a validated Pydantic model rather than a
  free dict?
- **`e_oswald_fallback_used` is context-wide.** Should it be per configuration,
  so a consumer can tell *which* polar rests on 0.8?
- **`_FALLBACK_E_OSWALD = 0.8` still exists** after the backfill. gh-956 says an
  unphysical or missing `e` should raise a **design warning** rather than be
  substituted silently. Should the fallback be removed entirely now that the
  backfill exists?
- **No per-key provenance.** `computed_at` covers the whole blob, so a consumer
  cannot tell that `v_x_mps` came from an older OP generation than `cd0`.
- **Dead code:** `_load_cg_agg` (`:1739`) and `_extract_scalar` (`:1316`).
  Delete, or is `_load_cg_agg` a deliberate alternative path kept for a reason
  nobody recorded?
- **Sync pipeline on an async server.** It is debounced and offloaded today, but
  nothing enforces `asyncio.to_thread` at the boundary — a future caller can
  block the event loop for the whole recompute.
