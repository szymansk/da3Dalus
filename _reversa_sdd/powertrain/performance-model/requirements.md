# performance-model

> Use-case specification, nested under the module
> [`powertrain`](../requirements.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Sources: `app/services/powertrain_performance.py`,
> `app/api/v2/endpoints/aeroplane/powertrain_performance.py`, ADR 0012.
> Endpoint contract: [`../contracts.md`](../contracts.md).

## Overview

Given a **motor**, a **battery** and a **propeller polar**, this use case
produces the propulsion curves the designer actually reasons with:
`T(V)`, `P_shaft(V)`, `η_prop(J)`, plus the advance ratio and RPM at every
sampled velocity. 🟢

Two motor models coexist and are selected **by data availability**: the
fixed-RPM power-limited chain (gh-615) when the motor's winding resistance is
unknown, and the QPROP 3-parameter torque balance (gh-1006) when `rm_ohm` is
present. The response says which one ran. 🟢

## Responsibilities

- Interpolate `Ct` and `Cp` at the advance ratio, clamping `J` to the dataset
  and reporting the clamp. 🟢
- Recompute `Pe = Ct·J/Cp` rather than reading the stored column. 🟢
- Model A: derive a fixed RPM from KV, pack voltage and throttle, and cap shaft
  power by the smaller of the motor and battery limits. 🟢
- Model B: solve the motor/propeller torque balance per velocity point by
  bisection. 🟢
- Emit a warning — never an exception — for every degenerate configuration. 🟢
- Resolve the three component references and hard-fail with 422 on missing
  specs. 🟢

**NOT this use case:** the polar dataset and its ingestion
(→ [`propeller-polars`](../propeller-polars/requirements.md)), the component
library (→ [`cots-powertrain-components`](../cots-powertrain-components/requirements.md)),
and the sizing/shopping questions
(→ [`powertrain-sizing`](../powertrain-sizing/requirements.md)).

## Business Rules

> Global ids from [`../../domain.md`](../../domain.md); `BR-PT*` from
> [`../requirements.md`](../requirements.md); `BR-PM*` are new here.

- **BR-65 — Nominal cell voltage is the *loaded* 3.7 V.** 🟢
  `_VOLTS_PER_LIPO_CELL = 3.7` (`:50`) — not the 4.2 V peak, which would inflate
  power by 13 %. `V_bat = cells · 3.7`; `V_terminal = V_bat · throttle`.
- **BR-PM1 — KV is always gear-aware.** 🟢
  `output_kv = kv_rpm_per_volt / (gear_ratio or 1)`. The raw KV is used in
  exactly one place in the whole codebase — the sizing modal — and deliberately
  so.
- **BR-PT13 — Model selection is by data, not by a flag.** 🟢
  `rm_ohm` absent or `≤ 0` ⇒ Model A, `estimated = True`;
  `rm_ohm > 0` ⇒ Model B, `estimated = False`. `MotorSpec.uses_qprop_model` is
  the derived predicate.
- **BR-PT14 — Model A's ceiling is the smaller of two limits.** 🟢
  ```
  n           = output_kv · V_bat · throttle          ← RPM is FIXED, not load-dependent
  P_elec_max  = min( max_current_a · 3.7 · cells_lipo_max ,      motor limit
                     (cap_mAh/1000) · C_rate · (cells·3.7) )     battery limit
  P_shaft_max = P_elec_max · η_motor                  η_motor = efficiency_pct/100 else 0.85
  per V:  J = V/(n·D) ;  Ct,Cp,Pe interpolated at J
          T = Ct·ρ·n²·D⁴                    clamped ≥ 0
          P = clip(Cp·ρ·n³·D⁵, 0, P_shaft_max)
          η_prop = clip(Pe, 0, 1)
  ```
- **BR-PT15 — Model B is a bisection over the torque balance.** 🟢
  ```
  Kv_si = output_kv · 2π/60   [rad/s per V]   Kt = 1/Kv_si  [Nm/A]
  I(n)       = (V_term − ω/Kv_si) / Rm                     back-EMF
  Q_motor(I) = (I − I₀)/Kv_si                              I₀ = io_no_load_a or 0
  Q_prop(n)  = Cp·ρ·n²·D⁵ / (2π)                           Cp at J = V/(n·D)
  solve Q_motor − Q_prop = 0 by BISECTION over 80 iterations
      bracket  rpm_hi = free-run  V_term·Kv_si·60/2π   (I → 0)
               rpm_lo = the back-EMF floor set by max_current_a
      r_lo ≤ 0 -> clamp to rpm_lo ;  r_hi ≥ 0 -> clamp to rpm_hi
  η_motor = (V_term − I·Rm)(I − I₀)/(V_term·I)   clipped to [0,1]
  P_shaft = Q·ω
  ```
  Solved **per velocity point**, which is what makes RPM load-dependent.
- **BR-66 — `η_prop` is J-dependent, never a flat constant.** 🟢
  `η_prop = clip(Pe, 0, 1)` at the interpolated advance ratio.
- **BR-PM2 — `Pe` is recomputed, not read.** 🟢 `Pe = Ct·J/Cp`, and `0` when
  `Cp ≤ 0` or `J = 0`. The stored `Pe` column is ignored.
- **BR-PT16 — `J` is clamped with an explicit warning.** 🟢 Rows are sorted by
  `J`; `np.interp` evaluates `Ct` and `Cp`; `J` outside `[J_min, J_max]` is
  clamped **and** `extrapolation_warning` is raised, producing a
  human-readable warning naming the affected sweep. The curve never runs off the
  dataset silently (ADR 0012).
- **BR-PT17 — `Ct` is clamped at 0.** 🟢 The slightly negative tail past zero
  thrust is discarded. 🟡 Windmilling drag is a genuine gap, not deliberate scope (`Q-PT-10`): a
  power-off descent reports zero propeller drag.
- **BR-PT18 — Torque is derived, never read.** 🟢 `Q = P/(2π·n)`; the stored
  `Torque_Nm` loses precision at 3 decimals for low-RPM rows.
- **BR-PT19 — RPM-aware callers pre-filter to the nearest RPM group.** 🟢
  `compute_prop_operating_point`, `compute_performance_curve` and
  `_prop_torque_demand` filter first; the J-only helper merges all RPM groups
  because `Ct(J)` is nearly RPM-independent for standard APC props. 🟡
- **BR-PT20 — Degenerate configurations warn, they do not raise.** 🟢
  - `prop_rpm ≤ 0` ⇒ an all-zero curve and *"Computed RPM is zero — check motor
    KV and battery voltage"*;
  - both power limits unknown ⇒ `V_bat × 100 A` with a warning;
  - `P_shaft_max < 0.1 W` ⇒ an infeasibility warning.
- **BR-PT21 — Air density is `1.225·exp(−h/8500)`.** 🟢 (`:346`) — the module's
  own exponential approximation — 🟢 replaced by one shared ISA helper wrapping `asb.Atmosphere` (`Q-PT-9`). Above a few
  hundred metres the two disagree.
- **BR-PM3 — Constants.** 🟢 `RHO_SEA_LEVEL = 1.225`, `G = 9.80665`,
  `_VOLTS_PER_LIPO_CELL = 3.7`, `_DEFAULT_ETA_MOTOR = 0.85`, bisection
  iterations `80`.
- **BR-PM4 — The velocity sweep is a linspace.** 🟢
  `np.linspace(v_min, v_max, n_points)`; the request schema validates
  `v_max_ms > v_min_ms` and `n_points ∈ [1, 500]` (the endpoint narrows it to
  `[1, 200]`).
- **BR-PM5 — Component resolution is the endpoint's job, and it raises HTTP
  directly.** 🟢 `_resolve_motor` / `_resolve_battery` / `_load_polar_rows`
  raise `HTTPException` rather than a domain exception, so those 404s and 422s
  bypass `_raise_http`. 🟡
- **BR-PM6 — The aeroplane is an anchoring formality.** 🟢 The endpoint 404s for
  an unknown UUID but reads **no** aeroplane data — the computation is entirely
  determined by the three component references and the sweep parameters. 🟡
- **BR-PM7 — The response names its own provenance.** 🟢
  `PowertrainPerformanceResponse.notes` carries model-provenance text, and every
  sample carries `estimated`.
- 🟢 **`Rm` is NOT a prerequisite: the fixed-RPM model stays the default** (`Q-PT-6`, expert consensus endorsed by the maintainer). Investigated and closed — D-Power publishes no `rm_ohm` and its PDFs are one-row-per-motor spec tables. Previously:, so Model B is dormant for
  every seeded motor and the shipped behaviour is Model A — whose own docstring
  calls it a simplification.
- 🟢 The Pydantic spec-model spellings are canonical; importers normalise (`Q-PT-4`). Previously `BatterySpec` read `c_rate` while the catalogue matcher reads
  `c_rating` / `discharge_c`. A battery imported under the other spelling loses
  its battery-side power limit here and silently falls back.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Sample the velocity range as a linspace of `n_points` | Must | `v_min 0, v_max 30, n_points 20` ⇒ 20 samples, first `0`, last `30` |
| RF-02 | Interpolate `Ct` and `Cp` at the advance ratio from the nearest RPM group | Must | A sweep reproduces the dataset's `Ct` at a sampled `J` |
| RF-03 | Recompute `Pe = Ct·J/Cp`, returning 0 when `Cp ≤ 0` or `J = 0` | Must | A stored `Pe` that disagrees with `Ct·J/Cp` does not reach the response |
| RF-04 | Clamp `J` to `[J_min, J_max]` and warn | Must | A sweep beyond the dataset returns the endpoint values **and** a warning naming the extrapolation |
| RF-05 | Clamp `Ct` at 0 | Must | A negative-thrust dataset row yields `thrust_n == 0`, never a negative |
| RF-06 | Use `output_kv = kv_rpm_per_volt / gear_ratio` | Must | A 2:1 geared motor produces half the RPM of the same raw KV ungeared |
| RF-07 | Use 3.7 V per cell, loaded | Must | A 3S pack is 11.1 V, not 12.6 V |
| RF-08 | Select Model B when `rm_ohm > 0`, Model A otherwise | Must | `estimated` is `false` / `true` respectively |
| RF-09 | Model A: hold RPM constant across the sweep | Must | Every sample has the same `rpm` |
| RF-10 | Model A: cap shaft power at `min(motor, battery limit) · η_motor` | Must | `p_shaft_w` never exceeds the cap at any velocity |
| RF-11 | Model B: solve the torque balance per point within 80 bisection iterations | Must | RPM falls monotonically with velocity for a fixed throttle |
| RF-12 | Model B: clamp a degenerate bracket to its endpoint | Must | `r_lo ≤ 0` returns `rpm_lo`; `r_hi ≥ 0` returns `rpm_hi`; neither diverges |
| RF-13 | Model B: clip `η_motor` to `[0, 1]` | Must | No sample reports an efficiency outside the unit interval |
| RF-14 | Derive torque as `P/(2π·n)` | Must | The stored `Torque_Nm` column is never read |
| RF-15 | Return an all-zero curve plus a warning when the computed RPM is zero | Must | Zero KV or zero throttle ⇒ zeros + *"Computed RPM is zero…"* |
| RF-16 | Warn and fall back to `V_bat × 100 A` when both power limits are unknown | Must | A motor and battery with no current/C-rate data still produce a curve, with a warning |
| RF-17 | Warn when `P_shaft_max < 0.1 W` | Should | The response carries an infeasibility warning |
| RF-18 | Resolve air density as `1.225·exp(−h/8500)` | Must | `altitude_m = 0` ⇒ 1.225; 1000 m ⇒ ≈ 1.089 |
| RF-19 | 404 for an unknown aeroplane, motor or battery id, or a wrong component type | Must | A `battery` id passed as `motor_component_id` ⇒ 404 |
| RF-20 | 422 for a missing required spec or an empty polar | Must | Motor without `kv_rpm_per_volt` / `cells_lipo_max`, battery without `cells` / `capacity_mah`, polar with no samples |
| RF-21 | Name the model that produced the curve | Should | `notes` distinguishes the fixed-RPM chain from the QPROP solve |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Correctness | The curve never extrapolates silently; the clamp is always reported (ADR 0012) | `interpolate_ct_cp_pe:278` | 🟢 |
| Correctness | Efficiency is a function of the operating point, not a constant | BR-66 | 🟢 |
| Correctness | Pack voltage uses the loaded 3.7 V, avoiding a 13 % power inflation | `:50`; BR-65 | 🟢 |
| Correctness | Torque is derived from power because the stored column is too coarse | BR-PT18 | 🟢 |
| Determinism | The solve is bounded at 80 iterations per point — the request cannot hang | `:569` | 🟢 |
| Robustness | Every degenerate configuration yields a curve plus a warning, never a 500 | BR-PT20 | 🟢 |
| Performance | Pure NumPy; the whole computation is O(n_points × 80) with no I/O after the initial loads | whole service | 🟢 |
| Portability | No AeroSandbox, no CadQuery — the route runs in the CI fast tier | whole service | 🟢 |
| Traceability | The response states which model ran, per sample and in prose | `estimated`, `notes` | 🟢 |
| Accuracy | 🟢 One shared ISA helper (`Q-PT-9`) | `:346` | 🔴 |

## Acceptance Criteria

```gherkin
Feature: Model selection

  Scenario: No winding resistance means the fixed-RPM model
    Given a motor whose specs omit rm_ohm
    When I compute the performance curve
    Then every sample has estimated true
    And every sample reports the same rpm

  Scenario: A winding resistance enables the QPROP model
    Given a motor with rm_ohm 0.05
    When I compute the performance curve
    Then every sample has estimated false
    And rpm decreases as velocity increases

Feature: Interpolation and clamping

  Scenario: Efficiency follows the advance ratio
    Given a propeller polar spanning J from 0.1 to 0.8
    When I compute the curve over that range
    Then eta_prop varies across the samples
    And no sample uses a constant 0.65

  Scenario: Extrapolation is clamped and reported
    Given a velocity sweep whose J exceeds the dataset maximum
    When I compute the curve
    Then Ct and Cp are evaluated at J_max
    And the response warnings mention the extrapolation

  Scenario: Negative thrust is clamped away
    Given a dataset row whose Ct is slightly negative
    When I compute the curve at that J
    Then thrust_n is 0
    And no warning is emitted for the clamp

  Scenario: Pe is recomputed, not read
    Given a sample row whose stored Pe is 0.99 while Ct·J/Cp is 0.55
    When I compute the curve at that J
    Then eta_prop is 0.55

Feature: Power limits

  Scenario: The smaller limit wins
    Given a motor limit of 400 W and a battery limit of 250 W
    When I compute the curve
    Then no sample exceeds 250 W times the motor efficiency

  Scenario: Both limits unknown falls back with a warning
    Given a motor with no max_current_a and a battery with no c_rate
    When I compute the curve
    Then the curve is produced
    And a warning explains the 100 A fallback

  Scenario: An infeasible ceiling is flagged
    Given a configuration whose P_shaft_max is below 0.1 W
    When I compute the curve
    Then a warning reports the infeasibility

Feature: Degenerate and error paths

  Scenario: Zero RPM is explained, not raised
    Given a motor KV and battery voltage whose product with throttle is 0
    When I compute the curve
    Then every sample is zero
    And a warning says "Computed RPM is zero — check motor KV and battery voltage"

  Scenario: A motor without KV is refused
    Given a brushless_motor component whose specs omit kv_rpm_per_volt
    When I POST the performance request
    Then the response status is 422
    And the message names the component id and name

  Scenario: A battery id passed as the motor is not found
    Given a component of type battery
    When I POST it as motor_component_id
    Then the response status is 404

  Scenario: A polar with no samples is refused
    Given a propeller polar whose sample table is empty
    When I POST the performance request
    Then the response status is 422
    And the message says the polar has no sample rows

  Scenario: An unknown aeroplane is refused even though its data is unused
    Given an unknown aeroplane UUID
    When I POST a fully valid performance request
    Then the response status is 404
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Interpolation with the clamp + warning (RF-02…RF-04) | Must | The single most load-bearing behaviour: it is the difference between a wrong curve and an honest one |
| Model A end to end (RF-06…RF-10) | Must | The shipped behaviour for every catalogue motor — no seeded motor has `rm_ohm` |
| Loaded 3.7 V and gear-aware KV (RF-06/RF-07) | Must | Both are 13 %-class errors if got wrong, and both are silent |
| Missing-spec 422s (RF-19/RF-20) | Must | The alternative is a NaN curve presented as a result |
| Zero-RPM and fallback warnings (RF-15/RF-16) | Must | Reachable configurations that must stay diagnosable |
| `Ct` clamp (RF-05) | Must | Prevents a negative thrust from being reported as a result |
| Model B (RF-11…RF-13) | Should | The physically better model, but dormant until a catalogue supplies `rm_ohm` |
| Derived torque (RF-14) | Should | Precision, not correctness — the stored column is available but coarse |
| Density model (RF-18) | Should | Sea level is the default; the divergence from ISA matters only at altitude |
| Model provenance in `notes` (RF-21) | Should | Diagnostic value; the `estimated` flag already carries the machine-readable answer |
| Windmilling / negative thrust | **Should** | 🟡 a genuine gap, not deliberate scope (`Q-PT-10`) |
| ISA atmosphere | **Must** | 🟢 decided (`Q-PT-9`): one shared helper wrapping `asb.Atmosphere` |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/powertrain_performance.py:48-51` | `RHO_SEA_LEVEL`, `G`, `_VOLTS_PER_LIPO_CELL`, `_DEFAULT_ETA_MOTOR` | 🟢 |
| `app/services/powertrain_performance.py:82` | `MotorSpec` (+ derived `output_kv`, `kv_si`, `eta_motor`, `max_electrical_power_w`, `uses_qprop_model`) | 🟢 |
| `app/services/powertrain_performance.py:174` | `BatterySpec` (+ derived `nominal_voltage_v`, `max_continuous_discharge_w`, `max_current_a`) | 🟢 |
| `app/services/powertrain_performance.py:210, 234, 252` | `PowertrainPerformanceRequest`, `PerformanceSample`, `PowertrainPerformanceResponse` | 🟢 |
| `app/services/powertrain_performance.py:278` | `interpolate_ct_cp_pe` | 🟢 |
| `app/services/powertrain_performance.py:346` | `_air_density` | 🟢 |
| `app/services/powertrain_performance.py:426` | `QpropOperatingPoint` | 🟢 |
| `app/services/powertrain_performance.py:569` | the 80-iteration bisection | 🟢 |
| `app/services/powertrain_performance.py` | `compute_performance_curve`, `compute_prop_operating_point`, `_prop_torque_demand` | 🟢 |
| `app/api/v2/endpoints/aeroplane/powertrain_performance.py` | the route, `_resolve_motor`, `_resolve_battery`, `_load_polar_rows`, `_raise_http` | 🟢 |
</content>
