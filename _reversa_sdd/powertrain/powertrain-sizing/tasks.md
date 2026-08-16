# powertrain-sizing — Implementation Tasks

> Executable sequence to re-implement the use case from the legacy behaviour.
> Every task cites the legacy file, a definition of done, and a confidence
> marker. Parent module tasks: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] `assumption_computation_context` on `aeroplanes` (gh-924) — module
      `aero-analysis`. Both paths read it; both must warn when it is empty.
- [ ] `design_assumptions_service.get_effective_assumption` and
      `PARAMETER_DEFAULTS` (`mass = 1.5`, `cd0 = 0.03`) — module
      `mission-and-sizing`.
- [ ] `endurance_service._power_required` and `DEFAULT_ETA_PROP/MOTOR/ESC`
      (`0.65 / 0.85 / 0.94`). **Do not** reimplement the drag polar.
- [ ] `components` with the `brushless_motor`, `battery` and `esc` types — see
      [`../cots-powertrain-components/tasks.md`](../cots-powertrain-components/tasks.md).
- [ ] `get_db()` session (ADR 0009). Both services are read-only.
- [ ] **No** AeroSandbox and **no** CadQuery — the solution space in particular
      must stay pure Python so it runs in the CI fast tier.

## Tasks

- [ ] **T-01 — Solution-space constants and the assumptions schema.**
  `G_DEFAULT = 9.80665`, `RHO_DEFAULT = 1.225`, `CELL_V_NOM = 3.7`,
  `CELL_V_SAG = 3.5`, `_PHASE1_PROP_DIAMETER_M = 0.30`,
  `_HYPERBOLA_SAMPLES = 40`; `SolutionSpaceAssumptions` with the 15 defaults
  (`cell_counts [2,3,4,6]`, `eta_prop_lo 0.65`, `eta_prop_hi 0.78`,
  `eta_motor 0.85`, `eta_esc 0.94`, `dod 0.80`, `esc_margin 1.4`,
  `c_margin 1.25`, `load_rpm_factor 0.85`, `prop_pd 0.65`, `t_target_min 10.0`,
  `v_top_mps None`, `rho 1.225`, `g 9.80665`) and their bounds.
  - Legacy origin: `app/services/powertrain_solution_space_service.py:64-75`,
    `app/schemas/powertrain_solution_space.py`
  - Definition of done: every default is reachable by omitting its query
    parameter; `_PHASE1_PROP_DIAMETER_M` carries the comment naming #615.
  - Confidence: 🟢

- [ ] **T-02 — `_p_aero` and `_p_elec`.**
  ```
  _p_aero: v <= 0 -> inf ; q = ½ρv² ; C_L = mg/(q·S) ;
           C_D = cd0 + C_L²/(π·e·AR) ; return q·S·C_D·v
  _p_elec: η = η_prop·η_motor·η_esc ; η <= 0 -> inf ; return p_aero/η
  ```
  - Legacy origin: `…:83-113`
  - Definition of done: a hand-computed level-flight power matches to 1e-9; both
    degenerate guards **return `inf`** rather than raising (reproduce, then
    record the non-finite-JSON risk as a gap).
  - Confidence: 🟢

- [ ] **T-03 — `_per_cell`.**
  `v_nom = S·3.7`, `v_sag = S·3.5`, **`i_peak = p_top_elec_w / v_sag`**,
  `cap_mah = energy_wh/v_nom·1000`, `c_min = (i_peak/(cap_mah/1000))·c_margin`,
  `esc_min = i_peak·esc_margin`,
  `rpm_target = (v_top/(0.30·prop_pd))·60`,
  `kv_approx = rpm_target/(v_nom·load_rpm_factor)`.
  - Legacy origin: `…:116-169`
  - Definition of done: a **regression test** pins `i_peak` against a
    hand-computed `P_top_elec / V_sag`, with a docstring naming gh-978 — the
    double-division must not be able to reappear.
  - Confidence: 🟢

- [ ] **T-04 — The η band with its documented inversion.**
  Evaluate every row three times — at the band mid-point, at `eta_prop_hi`
  (→ the `_lo` fields) and at `eta_prop_lo` (→ the `_hi` fields).
  - Legacy origin: `…:239-345`, `SolutionRow` docstring
  - Definition of done: `p_cruise_lo_w < p_cruise_w < p_cruise_hi_w`; a test
    fails if `_lo` is computed from `eta_prop_lo`.
  - Confidence: 🟢

- [ ] **T-05 — Shaft-power motor requirements.**
  `motor_peak_w = _p_aero(v_top)/η_prop_mid`,
  `motor_cont_w = _p_aero(v_cruise)/η_prop_mid`.
  - Legacy origin: `…:239-345`, `_catalog_motor_match:195-197`
  - Definition of done: the published figures are **shaft**, not aerodynamic,
    power — a test asserts they exceed `P_aero` by exactly `1/η_prop_mid`.
  - Confidence: 🟢

- [ ] **T-06 — `_build_hyperbola`.**
  40 points over `[cap_floor, 4·cap_floor]`; `c = i_peak/(cap/1000)`;
  `cap_floor ≤ 0` or `i_peak ≤ 0` ⇒ `([], [])`.
  - Legacy origin: `…:172-184`
  - Definition of done: 40 entries, the iso-current invariant holds at every
    sample, and both degenerate inputs return empty lists without raising.
  - Confidence: 🟢

- [ ] **T-07 — The three catalogue matchers.**
  motor `max_power_w ∥ max_continuous_power_w ≥ motor_peak_shaft_w`;
  battery `capacity_mah ≥ floor` **and** `c_rating ∥ discharge_c ≥ c_min`;
  ESC `max_current_a ∥ continuous_current_a ≥ esc_min_a`.
  - Legacy origin: `…:192-231`
  - Definition of done: each flag is `false` on an empty catalogue without
    failing the request; a **characterisation test** shows a battery carrying
    only `c_rate` matches nothing here, and its docstring names the vocabulary
    gap.
  - Confidence: 🟢

- [ ] **T-08 — `compute_solution_space` — input resolution and validation.**
  Six warned fallbacks (`s_ref_m2 → 0.25`, `e_oswald → 0.75`,
  `aspect_ratio → 7.0`, `v_cruise → 15.0`, `mass → 1.5`, `cd0 → 0.03` via the
  two-tier read), then `t_target_min > 0` and `v_top > v_cruise` as
  `ValidationDomainError`s, with `v_top` defaulting to `1.4·v_cruise`.
  - Legacy origin: `…:239-345`
  - Definition of done: an empty context yields **six** warnings and a 200; each
    validation yields a 422; a test asserts `cd0` is the only two-tier read.
  - Confidence: 🟢

- [ ] **T-09 — `SolutionRow`, `FeasibleRegion`, `ShoppingSpec` and the
  response.**
  All fields per [`../contracts.md`](../contracts.md), including the three
  `has_*_match` flags and the echoed `v_cruise_mps` / `v_top_mps` /
  `t_target_min`.
  - Legacy origin: `app/schemas/powertrain_solution_space.py`
  - Definition of done: one row, one feasible region and one shopping spec per
    requested cell count, with matching numbers across the three.
  - Confidence: 🟢

- [ ] **T-10 — The solution-space route.**
  `GET /aeroplanes/{aeroplane_id}/powertrain/solution-space`,
  `operation_id=get_powertrain_solution_space`, 15 optional query params,
  `cell_counts` multi-value; `ValidationDomainError → 422`,
  `NotFoundError → 404`, `InternalError → 500`, defensive `logger.exception` +
  500.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/powertrain_solution_space.py`
  - Definition of done: `?cell_counts=3&cell_counts=4` yields two rows; omitting
    every parameter uses the spec defaults. Reproduce the
    `HTTP_422_UNPROCESSABLE_CONTENT` spelling and record the inconsistency.
  - Confidence: 🟢

- [ ] **T-11 — Sweep constants and the raising shim.**
  `_DEFAULT_CD0 0.03`, `_E_OSWALD 0.8`, `_AR 8.0`, `_S_REF_M2 0.5`;
  `_required_power_w` raises `NotImplementedError` **by design**.
  - Legacy origin: `app/services/powertrain_sizing_service.py:44-47, 55`
  - Definition of done: a test asserts the shim raises. Record that these
    defaults differ from the solution space's (`0.75 / 7.0 / 0.25`).
  - Confidence: 🟢

- [ ] **T-12 — `_resolve_aero_params` (3-tier, gh-960).**
  explicit request field → `assumption_computation_context` → RC default, with a
  per-parameter warning naming the missing field.
  - Legacy origin: `app/services/powertrain_sizing_service.py:275-300`
  - Definition of done: each tier is exercised for each of the four parameters;
    a request field beats a populated context.
  - Confidence: 🟢

- [ ] **T-13 — Battery voltage resolution (gh-992).**
  `voltage_v → voltage → nominal_voltage → cells·3.7 → 11.1 V`.
  - Legacy origin: `app/services/powertrain_sizing_service.py`
  - Definition of done: a battery carrying only `cells: 4` resolves to 14.8 V,
    **not** 11.1 — a test must fail if the cell-count tier is skipped.
  - Confidence: 🟢

- [ ] **T-14 — `_evaluate_motor_battery_combo`.**
  Reject `capacity_mah ≤ 0` / `voltage ≤ 0`; `total_mass = airframe +
  motor.mass_g/1000 + battery.mass_g/1000`; `η_total = η_prop·η_motor·η_esc`;
  power **delegated** to `endurance_service._power_required`;
  `I_cruise = P/voltage` (999 when voltage is 0); reject
  `I_cruise > max_current_draw_a`; `t_flight = (cap_Ah/I_cruise)·0.8·60`;
  first-fit ESC; `confidence = min(t/target, 1.0)`; round `1 / 1 / 1 / 3` dp.
  - Legacy origin: `app/services/powertrain_sizing_service.py:230-273`
  - Definition of done: a spy asserts `_power_required` is called; a combination
    at 9.5 min against a 10 min target scores `0.95`; an over-current
    combination returns `None`. Reproduce the fact that the **propeller mass is
    absent** and record it as a gap.
  - Confidence: 🟢

- [ ] **T-15 — `_find_matching_esc` (characterisation).**
  The **first** ESC in query order whose `continuous_current_a` (with a
  `max_continuous_a` fallback) meets the cruise current; `None` when none fits.
  - Legacy origin: `app/services/powertrain_sizing_service.py`
  - Definition of done: a test with two fitting ESCs asserts the **first** is
    chosen and documents that the order is unspecified — do not add an
    `ORDER BY` here; record it as a gap.
  - Confidence: 🟢

- [ ] **T-16 — `size_powertrain`.**
  Resolve the aeroplane (404); load the three catalogues; empty motors and/or
  batteries ⇒ `[]` + a warning per missing category; cross-product; sort by
  confidence descending; return the top **10**.
  - Legacy origin: `app/services/powertrain_sizing_service.py:275-318`
  - Definition of done: 5 motors × 4 batteries yields ≤ 10 sorted candidates; an
    empty motor catalogue yields the exact gh-992 warning text.
  - Confidence: 🟢

- [ ] **T-17 — The sweep route.**
  `POST /aeroplanes/{aeroplane_id}/powertrain/sizing` (**not**
  `/powertrain_sizing`), 200, `operation_id=size_powertrain`,
  `PowertrainSizingRequest` / `PowertrainSizingResponse`.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/powertrain_sizing.py`
  - Definition of done: contract tests for 200 / 404 / 422; the path is asserted
    literally, since `code-analysis.md` records a different one.
  - Confidence: 🟢

- [ ] **T-18 — `get_modal_params` and its route.**
  `cd0` / `s_ref_m2` from the context with warnings; `altitude_m 0.0`,
  `eta_prop 0.65`, `eta_motor 0.85`; motors sorted by name with
  `efficiency_pct` defaulting to 85; the **raw** `kv_rpm_per_volt`.
  - Legacy origin: `app/services/powertrain_sizing_modal_service.py`,
    `app/api/v2/endpoints/aeroplane/powertrain_sizing_modal.py`
  - Definition of done: a geared motor's listed KV is its **raw** value — a test
    must fail if `output_kv` is used here (this is the documented exception to
    BR-65).
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — `_p_aero` / `_p_elec` numerics** against hand-computed values,
      plus both `inf` guards.
- [ ] **TT-02 — gh-978 regression:** `i_peak == p_top_elec_w / v_sag`, with a
      docstring naming the blocker.
- [ ] **TT-03 — Cell voltages:** 3S ⇒ 11.1 / 10.5; 4S ⇒ 14.8 / 14.0.
- [ ] **TT-04 — Band inversion:** `_lo` uses `eta_prop_hi`.
- [ ] **TT-05 — Shaft power:** `motor_peak_w == P_aero(v_top)/η_prop_mid`.
- [ ] **TT-06 — Margins:** `c_min == raw_c·1.25`, `esc_min_a == i_peak·1.4`.
- [ ] **TT-07 — KV approximation:** matches
      `(v_top/(0.30·prop_pd))·60 / (v_nom·load_rpm_factor)`.
- [ ] **TT-08 — Hyperbola:** 40 points, iso-current invariant, both degenerate
      inputs empty.
- [ ] **TT-09 — Fallback warnings:** an empty context yields six named
      warnings and a 200.
- [ ] **TT-10 — `cd0` two-tier read:** context → assumption → default.
- [ ] **TT-11 — Domain validation:** `t_target_min ≤ 0` and
      `v_top ≤ v_cruise` ⇒ 422; omitted `v_top` ⇒ `1.4·v_cruise`.
- [ ] **TT-12 — Catalogue flags:** all `false` on an empty catalogue; a
      `c_rate`-only battery matches nothing (characterisation).
- [ ] **TT-13 — Query parameters:** every one of the 15 overrides its default;
      `cell_counts` accepts multiple values.
- [ ] **TT-14 — Delegation guard:** the sweep calls `_power_required`; the local
      shim raises `NotImplementedError`.
- [ ] **TT-15 — 3-tier aero resolution:** request beats context beats default,
      per parameter, with the warning text.
- [ ] **TT-16 — Voltage walk:** all four keys in priority order.
- [ ] **TT-17 — Combination exclusion:** over-current, zero capacity, zero
      voltage.
- [ ] **TT-18 — Flight time:** the 80 % factor and the minute conversion.
- [ ] **TT-19 — Confidence:** continuous, capped at 1.0, rounded to 3 dp.
- [ ] **TT-20 — Ranking and cap:** descending order, at most 10.
- [ ] **TT-21 — ESC first-fit (characterisation)** with two fitting ESCs.
- [ ] **TT-22 — Empty catalogue warnings:** exact gh-992 text for motors and for
      batteries.
- [ ] **TT-23 — Modal raw KV** for a geared motor.
- [ ] **TT-24 — Default divergence (characterisation):** the same context-less
      aeroplane produces different `e` / `AR` / `S_ref` in the two paths — the
      test documents the inconsistency.
- [ ] **TT-25 — Fast-tier guard:** neither service imports `aerosandbox` or
      `cadquery`.

## Data Migration Tasks

None. Both services are read-only and persist nothing. 🟢

Their *inputs* have migration dependencies: the gh-924 context must have been
computed at least once (otherwise every request is served from the warned
fallbacks), and the component catalogue must be imported — see
[`../cots-powertrain-components/tasks.md`](../cots-powertrain-components/tasks.md)
TM-01…TM-02.

## Suggested Order

1. **T-01 → T-03** — constants, the two power functions and `_per_cell`. All
   pure, all testable with literals, and T-03 carries the gh-978 regression that
   must never regress.
2. **T-04 → T-06** the band, the shaft-power figures and the hyperbola — pure
   arithmetic on top of T-02/T-03.
3. **T-07** the catalogue matchers, which need only the component table.
4. **T-08 → T-10** the solution-space entry point and its route; the warned
   fallbacks are easiest to test once every downstream number is already pinned.
5. **T-11 → T-13** the sweep's constants and its two resolution helpers. They
   are independent of the solution space and can be built in parallel with 1–4.
6. **T-14 → T-16** the combination evaluation and the sweep, in that order —
   `_evaluate_motor_battery_combo` is where the delegation guard lives.
7. **T-17 → T-18** the remaining two routes.

## Pending Gaps (🔴)

- **Should `_find_matching_esc` choose the smallest or lightest fitting ESC?**
  Today it is the first row the database returns, with no `ORDER BY`.
- **Should the propeller's mass enter the sweep's total?** Motor and battery
  masses do; the propeller's has been known since gh-1000/1017.
- **Should the KV approximation use a real propeller diameter** from the APC
  database instead of the fixed 0.30 m Phase-1 constant (#615)?
- **Should `estimated_top_speed_ms` be computed** rather than echoing
  `target_top_speed_ms`?
- **Which RC defaults are canonical** — `e 0.75 / AR 7.0 / S 0.25` (solution
  space) or `e 0.8 / AR 8.0 / S 0.5` (sweep)? The same context-less aircraft is
  sized differently by the two endpoints.
- **Which spec keys are canonical** for the battery C-rate and the ESC current?
  Three vocabularies coexist across this use case, the matchers and
  `BatterySpec`.
- **Should a stale context be detectable?** The warnings fire on *missing*
  values only, so an out-of-date sizing is indistinguishable from a fresh one.
- **Should `inf` be prevented from reaching the response**, or should these
  routers adopt `NonFiniteSafeJSONResponse` (ADR 0012)?
- **Should a candidate with no fitting ESC be flagged** rather than returned
  with `esc_id = null`?
- **Should the cross-product be bounded** for large catalogues?
- **Should the sizing router log its catch-all 500?** It currently does not.
- **Should `HTTP_422_UNPROCESSABLE_CONTENT` and `..._ENTITY` be unified?**
</content>
