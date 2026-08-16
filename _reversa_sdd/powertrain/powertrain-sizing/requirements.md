# powertrain-sizing

> Use-case specification, nested under the module
> [`powertrain`](../requirements.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Sources: `app/services/powertrain_solution_space_service.py`,
> `powertrain_sizing_service.py`, `powertrain_sizing_modal_service.py`,
> `endurance_service.py`, the three endpoint modules, ADR 0004, ADR 0012.
> Endpoint contract: [`../contracts.md`](../contracts.md).

## Overview

Two sizing answers to two different questions, plus the modal that pre-fills
them:

- **Solution space** (gh-975) — *"what must I shop for?"* Given the mission and
  the aero context, it computes the **required** battery capacity, C-rate, ESC
  rating, motor power and KV per LiPo cell count, across a propeller-efficiency
  band, in pure Python. 🟢
- **Catalog sweep** — *"which of the parts I already own fit?"* A full
  motor × battery cross-product, with ESCs matched rather than swept, ranked by
  a continuous confidence score. 🟢
- **Sizing modal** — the pre-fill defaults for the frontend dialog. 🟢

## Responsibilities

- Read the aero invariants from the gh-924 computation context and warn on every
  fallback. 🟢
- Compute `P_aero`, `P_elec` and the per-cell-count specs at three propeller
  efficiencies to produce a band. 🟢
- Sample the feasible-region C-rate hyperbola and publish a shopping spec. 🟢
- Report catalogue availability per row. 🟢
- Sweep the catalogue, exclude infeasible combinations, and rank the top 10. 🟢
- Delegate the drag polar to `endurance_service._power_required` — never
  duplicate it. 🟢
- Serve the modal defaults with the **raw** motor KV. 🟢

**NOT this use case:** the propulsion curves
(→ [`performance-model`](../performance-model/requirements.md)), the component
library (→ [`cots-powertrain-components`](../cots-powertrain-components/requirements.md)),
and the endurance endpoint itself (→ `mission-and-sizing`).

## Business Rules

> Global ids from [`../../domain.md`](../../domain.md); `BR-PT*` from
> [`../requirements.md`](../requirements.md); `BR-SZ*` are new here.

### Solution space

- **BR-PT22 — The physics.** 🟢
  ```
  C_L(V)    = 2·m·g / (ρ·V²·S_ref)
  C_D(V)    = cd0 + C_L² / (π·e·AR)
  P_aero(V) = ½·ρ·V³·S_ref·C_D(V)          = q·S_ref·C_D·V
  P_elec(V) = P_aero / (η_prop·η_motor·η_esc)
  E_Wh      = P_elec(V_cruise) · t_target_h / DoD
  ```
  (`_p_aero:83`, `_p_elec:108`.) `V ≤ 0` returns `inf` rather than raising;
  `η ≤ 0` likewise. 🟡
- **BR-PT23 — No double-counting of efficiency.** 🟢
  `I_peak = P_top_elec / V_sag`, because `P_top_elec` is **already** battery
  power. Dividing again by `η_motor·η_esc` was the gh-978 BLOCKER; the
  docstring at `_per_cell:129-133` states it explicitly.
- **BR-PT24 — Per-cell derivation.** 🟢 (`_per_cell:116-169`)
  ```
  v_nom   = S · CELL_V_NOM (3.7)      v_sag = S · CELL_V_SAG (3.5)
  i_peak  = p_top_elec_w / v_sag
  cap_mAh = energy_wh / v_nom · 1000
  raw_c   = i_peak / (cap_mAh/1000)   c_min = raw_c · c_margin
  esc_min = i_peak · esc_margin
  rpm_target = (v_top / (D · prop_pd)) · 60      D from the APC polar database (Q-PT-3) 🟢
  kv_approx  = rpm_target / (v_nom · load_rpm_factor)   (0.0 only if v_nom ≤ 0)
  ```
- **BR-SZ1 — Motor figures are shaft power, deliberately.** 🟢
  `motor_peak_shaft_w = P_aero(V_top)/η_prop_mid`,
  `motor_cont_shaft_w = P_aero(V_cruise)/η_prop_mid` — so the comparison against
  a catalogue `max_power_w` (a shaft rating) is apples-to-apples
  (`_catalog_motor_match:192-207`).
- **BR-PT25 — Three evaluations produce a band, with an inversion.** 🟢 Mid, low
  and high `η_prop`; `p_cruise_lo_w = p_cruise_hi_e` because a *more* efficient
  propeller needs *less* power. The `SolutionRow` docstring documents it.
- **BR-PT26 — The feasible region is a sampled hyperbola.** 🟢
  `_build_hyperbola:172` samples `C = i_peak/(cap/1000)` at
  `_HYPERBOLA_SAMPLES = 40` points over `[cap_floor, 4·cap_floor]`;
  `cap_floor ≤ 0` or `i_peak ≤ 0` returns two **empty** lists rather than
  raising.
- **BR-PT27 / ADR 0004 — The context is the single source, and every fallback
  is warned about.** 🟢 (`compute_solution_space:265-325`)
  | Input | Source | Fallback | Warning |
  |---|---|---|---|
  | `s_ref_m2` | `ctx["s_ref_m2"]` | `0.25 m²` | *"run recompute first"* |
  | `e_oswald` | `ctx["e_oswald"]` | `0.75` | idem |
  | `aspect_ratio` | `ctx["aspect_ratio"]` | `7.0` | idem |
  | `v_cruise` | `ctx["v_cruise_mps"]` ∥ `ctx["v_md_mps"]` | `15.0 m/s` | idem |
  | `mass` | `get_effective_assumption(…, "mass")` | `PARAMETER_DEFAULTS["mass"] = 1.5 kg` | *"mass not set"* |
  | `cd0` | `ctx["cd0"]` → assumption `cd0` | `0.03` | *"not set in context or design assumptions"* |
  Note `cd0` is the only two-tier read; the others go straight to their default.
- **BR-PT28 — Two domain validations.** 🟢 `t_target_min ≤ 0` and
  `v_top ≤ v_cruise` raise `ValidationDomainError` → 422. `v_top` defaults to
  `1.4 · v_cruise`.
- **BR-SZ2 — The tunable assumptions and their defaults.** 🟢
  `cell_counts [2,3,4,6]` · `eta_prop_lo 0.65` / `eta_prop_hi 0.78` ·
  `eta_motor 0.85` · `eta_esc 0.94` · `dod 0.80` · `esc_margin 1.4` ·
  `c_margin 1.25` · `load_rpm_factor 0.85` · `prop_pd 0.65` ·
  `t_target_min 10.0` · `v_top_mps None` · `rho 1.225` · `g 9.80665`.
- **BR-SZ3 — The solution space is pure Python.** 🟢 No CadQuery, no
  AeroSandbox — a deliberate choice so it runs in the CI fast tier.
- **BR-SZ4 — Catalogue matching uses three different key vocabularies.** 🟢
  motor `max_power_w ∥ max_continuous_power_w`; battery `capacity_mah` **and**
  `c_rating ∥ discharge_c`; ESC `max_current_a ∥ continuous_current_a`. 🟢 The Pydantic spellings are canonical (`Q-PT-4`). Previously none
  of these matches `BatterySpec.c_rate` or the sizing sweep's
  `continuous_current_a ∥ max_continuous_a`.

### Catalog sweep

- **BR-PT29 — Motor × battery cross-product; ESCs are matched.** 🟢
  ```
  total_mass = airframe_mass_kg + motor.mass_g/1000 + battery.mass_g/1000
  η_total    = η_prop · η_motor · η_esc          defaults 0.65 · 0.85 · 0.94
  P_cruise   = endurance_service._power_required(ρ, V, cd0, e, AR, m, S, η_total)
  I_cruise   = P_cruise / V_pack
  reject if  max_current_draw_a and I_cruise > max_current_draw_a
  t_flight   = (cap_Ah / I_cruise) · 0.8 · 60          [min]
  ESC        = all-of gate on PEAK current (Q-PT-1) 🟢
  confidence = min(t_flight / t_target, 1.0)
  sort by confidence desc ; return the top 10
  ```
- **BR-PT30 — The drag polar is delegated, not duplicated.** 🟢
  `endurance_service._power_required` (gh-490 Model A) is the single drag polar:
  `P_req(V) = ½ρV²S·C_D(V)·V / η_total` with
  `C_D = cd0 + C_L²/(π·e·AR)` and `C_L = 2mg/(ρV²S)`. The legacy
  `_required_power_w` shim (`powertrain_sizing_service.py:55`) raises
  `NotImplementedError` **by design** — an estimate-only mode without geometry
  is no longer allowed.
- **BR-PT31 — Aero parameters follow a 3-tier priority (gh-960).** 🟢
  explicit request field → `assumption_computation_context` → RC-typical default
  (`cd0 0.03`, `e 0.8`, `AR 8.0`, `S_ref 0.5 m²`), with a per-parameter warning
  naming the missing field. 🟡 Note the defaults differ from the solution
  space's (`0.03 / 0.75 / 7.0 / 0.25`).
- **BR-PT32 — Battery voltage resolution walks four keys.** 🟢
  `voltage_v → voltage → nominal_voltage → cells·3.7 → 11.1 V`, so a
  schema-valid battery is not mis-read as 3S (gh-992).
- **BR-SZ5 — 80 % of the rated capacity is usable.** 🟢 The `0.8` factor in
  `t_flight` (`:256`).
- **BR-SZ6 — Confidence is continuous, not a cliff.** 🟢
  `min(t_flight/t_target, 1.0)`, rounded to 3 dp (gh-992). A combination that
  falls 5 % short is ranked just below one that meets the target, rather than
  being discarded.
- **BR-PT33 — An empty catalogue explains itself.** 🟢 No motors and/or no
  batteries ⇒ `recommendations: []` **plus** a warning per missing category
  naming the remedy (*"import the D-Power catalog"*).
- **BR-SZ7 — A candidate may have no ESC.** 🟢 `esc_id` / `esc_name` are `None`
  when nothing fits, and the candidate is still returned, unflagged. 🟡
- **BR-SZ8 — `estimated_top_speed_ms` echoes the request.** 🟢 It is
  `round(request.target_top_speed_ms, 1)` — a copy of the input, not a computed
  achievable speed. 🟡 The field name promises more than it delivers.

### Sizing modal

- **BR-SZ9 — Same fallback pattern, different consumer.** 🟢 `cd0` and
  `s_ref_m2` from the gh-924 context with warnings; `DEFAULT_MOTOR_ETA = 0.85`;
  `DEFAULT_ETA_PROP = 0.65`; motors sorted by name with `efficiency_pct`
  defaulting to 85.
- **BR-65 (exception) — The modal shows the RAW KV.** 🟢 Deliberately **not**
  `output_kv`, because the designer is picking a motor, not an output shaft.
  This is the only place in the codebase where the gear-aware rule is not
  applied.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Compute one `SolutionRow` per requested cell count | Must | `?cell_counts=3&cell_counts=4` ⇒ exactly two rows |
| RF-02 | Derive `v_nom = S·3.7` and `v_sag = S·3.5` | Must | A 4S row reports 14.8 V and 14.0 V |
| RF-03 | Compute `I_peak = P_top_elec / V_sag` without a second efficiency division | Must | A hand-computed regression value matches to 1e-9 (gh-978 guard) |
| RF-04 | Publish the η band with the documented inversion | Must | `p_cruise_lo_w < p_cruise_w < p_cruise_hi_w` for a normal band |
| RF-05 | Publish `motor_peak_w` / `motor_cont_w` as **shaft** power | Must | They equal `P_aero/η_prop_mid` at `V_top` and `V_cruise` |
| RF-06 | Derive `c_min` and `esc_min_a` including their margins | Must | `c_min == raw_c · 1.25`; `esc_min_a == i_peak · 1.4` at the defaults |
| RF-07 | Approximate KV from a fixed 0.30 m propeller | Must | The value matches `rpm_target/(v_nom·load_rpm_factor)` |
| RF-08 | Sample the feasible-region hyperbola at 40 points | Must | 40 entries; `C·cap/1000 == i_peak` at every one |
| RF-09 | Return empty curves for a degenerate hyperbola | Must | `cap_floor ≤ 0` or `i_peak ≤ 0` ⇒ two empty lists, no exception |
| RF-10 | Publish a `ShoppingSpec` per cell count | Should | One per row, with the same numbers |
| RF-11 | Report catalogue availability per row | Should | All three flags `false` on an empty catalogue, request still 200 |
| RF-12 | Warn on every aero/mass fallback | Must | An empty context yields ≥ 4 warnings naming the inputs |
| RF-13 | Reject `t_target_min ≤ 0` and `v_top ≤ v_cruise` | Must | Both ⇒ 422 |
| RF-14 | Default `v_top` to `1.4 · v_cruise` | Must | Omitting it yields 21 m/s for a 15 m/s cruise |
| RF-15 | Accept all 15 assumptions as optional query parameters | Should | Any subset overrides; the rest keep their spec defaults |
| RF-16 | Sweep motor × battery and rank the top 10 by confidence | Must | ≤ 10 recommendations, descending |
| RF-17 | Include motor and battery mass in the total | Must | `total_mass = airframe + motor.mass_g/1000 + battery.mass_g/1000` |
| RF-18 | Delegate the cruise power to `endurance_service._power_required` | Must | A spy asserts the call; the local shim still raises `NotImplementedError` |
| RF-19 | Exclude a combination exceeding `max_current_draw_a` | Must | Such a combination never appears |
| RF-20 | Apply the 80 % usable-capacity factor | Must | `t_flight == (cap_Ah/I)·0.8·60` |
| RF-21 | Match the first ESC meeting the cruise current | Should | The candidate carries that ESC; none fitting ⇒ `esc_id = null` |
| RF-22 | Score confidence continuously | Must | A combination at 95 % of the target scores 0.95, not 0 |
| RF-23 | Resolve aero parameters in 3 tiers with warnings | Must | Request → context → default, one warning per defaulted parameter |
| RF-24 | Resolve battery voltage through four keys | Must | A battery with only `cells` resolves to `cells·3.7`, not 11.1 |
| RF-25 | Explain an empty catalogue instead of returning a bare empty list | Must | No motors ⇒ a warning naming the remedy |
| RF-26 | Serve modal defaults with the raw KV and per-default warnings | Should | The response carries the motor's `kv_rpm_per_volt`, not `output_kv` |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Correctness | Battery power is not divided by efficiency twice | `_per_cell:129-139`; gh-978 | 🟢 |
| Correctness | Motor comparisons are shaft-vs-shaft, never shaft-vs-aero | `_catalog_motor_match:192-207` | 🟢 |
| Correctness | There is exactly one drag polar in the codebase | `_power_required`; the raising shim | 🟢 |
| Honesty | Every defaulted input produces a named warning (ADR 0012) | `compute_solution_space:265-325`, `_resolve_aero_params` | 🟢 |
| Honesty | An empty result explains itself rather than looking broken | gh-992 | 🟢 |
| Performance | Pure Python/NumPy — the solution space runs in the CI fast tier | module docstring | 🟢 |
| Performance | The sweep is O(motors × batteries) with a linear ESC scan per combination | `size_powertrain:275-318` | 🟡 unbounded by design |
| Robustness | Degenerate hyperbola inputs return empty curves rather than raising | `_build_hyperbola:179-180` | 🟢 |
| Determinism | 🟢 An all-of peak-current gate removes the ordering dependence (`Q-PT-1`) | `_find_matching_esc` | 🟢 |
| Portability | Neither service imports AeroSandbox or CadQuery | both services | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Solution space

  Scenario: One row per cell count with the right voltages
    Given an aeroplane with a computed aero context
    When I GET the solution space with cell_counts 3 and 4
    Then there are two rows
    And the 4S row has v_nom_v 14.8 and v_sag_v 14.0

  Scenario: Peak current does not double-count efficiency
    Given a top-speed electrical power of 300 W and a 4S pack
    When I compute the solution space
    Then i_peak_a is 300 / 14.0
    And it is not divided again by eta_motor or eta_esc

  Scenario: The efficiency band is inverted as documented
    Given eta_prop_lo 0.65 and eta_prop_hi 0.78
    When I compute the solution space
    Then p_cruise_lo_w is less than p_cruise_w
    And p_cruise_hi_w is greater than p_cruise_w

  Scenario: Missing context is warned about, not fatal
    Given an aeroplane whose assumption_computation_context is empty
    When I GET the solution space
    Then the response status is 200
    And warnings name s_ref_m2, e_oswald, aspect_ratio and v_cruise

  Scenario: An impossible mission is refused
    Given v_top_mps 12 and a cruise speed of 15
    When I GET the solution space
    Then the response status is 422

  Scenario: A non-positive flight time is refused
    Given t_target_min 0
    When I GET the solution space
    Then the response status is 422

  Scenario: The feasible region is a 40-point hyperbola
    Given a computed row with i_peak 20 A and a capacity floor of 2000 mAh
    When I read its feasible region
    Then capacity_curve_mah has 40 entries
    And every c_rate_curve entry equals i_peak divided by capacity in Ah

  Scenario: A degenerate hyperbola is empty, not an error
    Given a capacity floor of 0
    When I build the hyperbola
    Then both curves are empty lists

Feature: Catalog sweep

  Scenario: Candidates are ranked and capped
    Given 5 motors and 4 batteries
    When I POST a sizing request
    Then at most 10 recommendations are returned
    And confidence is non-increasing across the list

  Scenario: Confidence is continuous
    Given a combination achieving 9.5 minutes against a 10 minute target
    When I POST a sizing request
    Then its confidence is 0.95

  Scenario: An over-current combination is excluded
    Given max_current_draw_a 20 and a combination drawing 25 A at cruise
    When I POST a sizing request
    Then that combination is absent

  Scenario: The drag polar is delegated
    Given a sizing request
    When the sweep runs
    Then endurance_service._power_required is called
    And the local _required_power_w shim raises NotImplementedError if invoked

  Scenario: Battery voltage falls back to the cell count
    Given a battery whose specs carry only cells 3 and capacity_mah 2200
    When I POST a sizing request
    Then the pack voltage used is 11.1 V from cells times 3.7

  Scenario: An empty catalogue explains itself
    Given no brushless_motor components
    When I POST a sizing request
    Then recommendations is empty
    And a warning names the missing motors and how to add them

Feature: Sizing modal

  Scenario: The raw KV is shown
    Given a motor with kv_rpm_per_volt 1000 and gear_ratio 2
    When I GET the sizing-modal params
    Then the listed KV is 1000
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Solution-space physics + per-cell derivation (RF-01…RF-07) | Must | The "what do I buy" answer; every number is acted on by a purchase |
| The gh-978 non-double-count (RF-03) | Must | A previously shipped blocker; the error is invisible and doubles the current estimate |
| Shaft-power motor figures (RF-05) | Must | Comparing shaft to aero power would understate the motor by ~35 % |
| Fallback warnings + domain validation (RF-12…RF-14) | Must | The defaults are only trustworthy because they are announced (ADR 0012) |
| Sweep ranking, exclusions, delegation (RF-16…RF-20, RF-22) | Must | The "what do I own" answer; the delegation keeps one drag polar in the codebase |
| Battery voltage walk (RF-24) | Must | gh-992 — a mis-read pack voltage silently halves the flight time |
| Empty-catalogue warnings (RF-25) | Must | gh-992 — an empty table reads as a broken feature |
| Feasible region + shopping spec (RF-08…RF-10) | Should | Presentation of numbers already computed |
| Catalogue availability flags (RF-11) | Should | Decorative; the required specs stand alone |
| Tunable query parameters (RF-15) | Should | Every one has a spec default |
| ESC selection by an all-of gate on peak current | **Must** | 🟢 decided (`Q-PT-1`): replaces first-fit; ordering no longer matters |
| Modal defaults with raw KV (RF-26) | Should | UI convenience over data available elsewhere |
| A computed `estimated_top_speed_ms` | Won't | 🟡 the field echoes the request; nothing computes an achievable speed |
| Propeller mass in the sweep total | **Must** | 🟢 decided (`Q-PT-2`): the selected propeller's `weight_g` enters `total_mass` |
| KV from a real propeller diameter | **Must** | 🟢 decided (`Q-PT-3`): APC polar database |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/powertrain_solution_space_service.py:64-75` | `G_DEFAULT`, `RHO_DEFAULT`, `CELL_V_NOM/SAG`, `_PHASE1_PROP_DIAMETER_M`, `_HYPERBOLA_SAMPLES` | 🟢 |
| `…:83, 108, 116, 172` | `_p_aero`, `_p_elec`, `_per_cell`, `_build_hyperbola` | 🟢 |
| `…:192-231` | `_catalog_motor_match`, `_catalog_battery_match`, `_catalog_esc_match` | 🟢 |
| `…:239-345` | `compute_solution_space` incl. the six warned fallbacks and the two validations | 🟢 |
| `app/schemas/powertrain_solution_space.py` | `SolutionSpaceAssumptions`, `SolutionRow`, `FeasibleRegion`, `ShoppingSpec`, `PowertrainSolutionSpaceResponse` | 🟢 |
| `app/services/powertrain_sizing_service.py:44-47` | `_DEFAULT_CD0/_E_OSWALD/_AR/_S_REF_M2` | 🟢 |
| `app/services/powertrain_sizing_service.py:55` | `_required_power_w` shim | 🟡 raises by design |
| `…:230-273` | `_evaluate_motor_battery_combo`, `_find_matching_esc`, `_compute_confidence` | 🟢 |
| `…:275-318` | `size_powertrain`, `_resolve_aero_params`, the empty-catalogue warnings | 🟢 |
| `app/schemas/powertrain_sizing.py` | `PowertrainSizingRequest`, `PowertrainCandidate`, `PowertrainSizingResponse` | 🟢 |
| `app/services/powertrain_sizing_modal_service.py` | `get_modal_params` | 🟢 |
| `app/services/endurance_service.py:40-120` | `_power_required`, `DEFAULT_ETA_PROP/MOTOR/ESC` | 🟢 owned by `mission-and-sizing` |
| `app/api/v2/endpoints/aeroplane/powertrain_solution_space.py` | route + 15 query params | 🟢 |
| `app/api/v2/endpoints/aeroplane/powertrain_sizing.py` | `POST …/powertrain/sizing` | 🟢 |
| `app/api/v2/endpoints/aeroplane/powertrain_sizing_modal.py` | `GET …/powertrain/sizing-modal-params` | 🟢 |
</content>
