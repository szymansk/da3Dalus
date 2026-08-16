# performance-model — Implementation Tasks

> Executable sequence to re-implement the use case from the legacy behaviour.
> Every task cites the legacy file, a definition of done, and a confidence
> marker. Parent module tasks: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] `propeller_polars` + `propeller_polar_samples` populated — see
      [`../propeller-polars/tasks.md`](../propeller-polars/tasks.md) T-01, T-02,
      T-05. Unit tests may use hand-built sample lists instead.
- [ ] `components` with the `brushless_motor` and `battery` types — see
      [`../cots-powertrain-components/tasks.md`](../cots-powertrain-components/tasks.md).
- [ ] `aeroplanes` with a public `uuid` (the route 404s on it; nothing else).
- [ ] NumPy. **No** AeroSandbox and **no** CadQuery — this route must run in the
      CI fast tier.
- [ ] `get_db()` session (ADR 0009) — the use case is read-only.

## Tasks

- [ ] **T-01 — Constants.**
  `RHO_SEA_LEVEL = 1.225`, `G = 9.80665`, `_VOLTS_PER_LIPO_CELL = 3.7`,
  `_DEFAULT_ETA_MOTOR = 0.85`, bisection iterations `80`.
  - Legacy origin: `app/services/powertrain_performance.py:48-51, 569`
  - Definition of done: `3.7` appears once, as a named constant, with the
    comment explaining that 4.2 V would inflate power by 13 %. Record that
    `G = 9.80665` here diverges from `mass_cg_service.GRAVITY = 9.81`.
  - Confidence: 🟢

- [ ] **T-02 — `MotorSpec` with its derived properties.**
  Fields `kv_rpm_per_volt (>0)`, `gear_ratio (>0)`, `efficiency_pct (0-100)`,
  `cells_lipo_max (≥1)`, `io_no_load_a`, `max_current_a`,
  `continuous_current_a`, `rm_ohm`; derived `output_kv = kv/(gear_ratio or 1)`,
  `kv_si = output_kv·2π/60`, `eta_motor = efficiency_pct/100 else 0.85`,
  `max_electrical_power_w`, **`uses_qprop_model = rm_ohm is not None and
  rm_ohm > 0`**.
  - Legacy origin: `app/services/powertrain_performance.py:82`
  - Definition of done: a 2:1 geared motor yields half the `output_kv`;
    `uses_qprop_model` is the single predicate driving model selection.
  - Confidence: 🟢

- [ ] **T-03 — `BatterySpec` with its derived properties.**
  `cells (≥1)`, `capacity_mah (>0)`, `c_rate`; derived
  `nominal_voltage_v = cells·3.7`, `max_continuous_discharge_w`,
  `max_current_a`.
  - Legacy origin: `app/services/powertrain_performance.py:174`
  - Definition of done: a 3S pack reports 11.1 V. Reproduce the fact that only
    `c_rate` is read (**not** `c_rating` / `discharge_c`) and record the
    vocabulary gap.
  - Confidence: 🟢

- [ ] **T-04 — `interpolate_ct_cp_pe`.**
  Sort by `J`; `np.interp` on `Ct` and `Cp`; clamp `J` to `[J_min, J_max]` and
  set `extrapolation_warning`; clamp `Ct` at 0; recompute
  `Pe = Ct·J/Cp`, `0` when `Cp ≤ 0` or `J = 0`.
  - Legacy origin: `app/services/powertrain_performance.py:278`
  - Definition of done: in-range interpolation reproduces the dataset; a `J`
    above `J_max` returns the endpoint value **and** the warning flag; a stored
    `Pe` of 0.99 that disagrees with `Ct·J/Cp = 0.55` yields 0.55; a negative
    `Ct` row yields 0.
  - Confidence: 🟢

- [ ] **T-05 — `_air_density`.**
  `1.225 · exp(−h/8500)`.
  - Legacy origin: `app/services/powertrain_performance.py:346`
  - Definition of done: 0 m ⇒ 1.225; 1000 m ⇒ ≈ 1.089. Record the divergence
    from `asb.Atmosphere` as a gap; **do not** substitute the ISA model.
  - Confidence: 🟢

- [ ] **T-06 — Model A, the fixed-RPM chain.**
  `V_bat = cells·3.7`; `n = output_kv · V_bat · throttle` (constant across the
  sweep); `P_elec_max = min(motor limit, battery limit)`;
  `P_shaft_max = P_elec_max · η_motor`; per point
  `T = max(Ct·ρ·n²·D⁴, 0)`, `P = clip(Cp·ρ·n³·D⁵, 0, P_shaft_max)`,
  `η_prop = clip(Pe, 0, 1)`, `estimated = True`.
  - Legacy origin: `app/services/powertrain_performance.py` (curve loop)
  - Definition of done: every sample reports the **same** `rpm`; no sample
    exceeds `P_shaft_max`; a test computes the curve with 4.2 V per cell and
    asserts it differs by ~13 % (guards BR-65 against a future "fix").
  - Confidence: 🟢

- [ ] **T-07 — Model B, the QPROP torque balance.**
  `I(n) = (V_term − ω/Kv_si)/Rm`; `Q_motor = (I − I₀)/Kv_si`;
  `Q_prop(n) = Cp·ρ·n²·D⁵/(2π)` with `Cp` at `J = V/(n·D)`; bisection over 80
  iterations between the free-run RPM and the back-EMF floor;
  `η_motor = (V_term − I·Rm)(I − I₀)/(V_term·I)` clipped to `[0,1]`;
  `P_shaft = Q·ω`; `estimated = False`.
  - Legacy origin: `app/services/powertrain_performance.py:569`
  - Definition of done: RPM decreases monotonically with velocity at fixed
    throttle; the loop runs a bounded 80 iterations; `η_motor` never leaves
    `[0,1]`.
  - Confidence: 🟢

- [ ] **T-08 — The two bracket clamps.**
  `r_lo ≤ 0` ⇒ return `rpm_lo`; `r_hi ≥ 0` ⇒ return `rpm_hi`.
  - Legacy origin: `app/services/powertrain_performance.py` (bracket setup)
  - Definition of done: two tests construct each degenerate bracket and assert a
    finite clamped RPM — the solver must never raise, loop forever or return
    `NaN`.
  - Confidence: 🟢

- [ ] **T-09 — Model selection and the `estimated` flag.**
  `uses_qprop_model` chooses the path; `estimated` is its inverse on every
  sample; `notes` names the model in prose.
  - Legacy origin: `MotorSpec:82`, `PowertrainPerformanceResponse:252`
  - Definition of done: one test per branch asserting both `estimated` and the
    presence of the model name in `notes`.
  - Confidence: 🟢

- [ ] **T-10 — Degenerate warnings.**
  `prop_rpm ≤ 0` ⇒ an all-zero curve + *"Computed RPM is zero — check motor KV
  and battery voltage"*; both power limits unknown ⇒ `V_bat × 100 A` + warning;
  `P_shaft_max < 0.1 W` ⇒ an infeasibility warning.
  - Legacy origin: `app/services/powertrain_performance.py`
  - Definition of done: each case returns **200** with its exact warning text.
    A test must fail if any of them raises (ADR 0012).
  - Confidence: 🟢

- [ ] **T-11 — `compute_performance_curve`.**
  `np.linspace(v_min, v_max, n_points)`; per point delegate to the selected
  model; assemble `PerformanceSample`s, `p_available_w`, `warnings[]` and
  `notes`.
  - Legacy origin: `app/services/powertrain_performance.py`
  - Definition of done: `v_min 0, v_max 30, n_points 20` yields 20 samples with
    the first at 0 and the last at 30; the extrapolation warning appears once,
    not once per point.
  - Confidence: 🟢

- [ ] **T-12 — `compute_prop_operating_point` / `QpropOperatingPoint`.**
  A single operating point returning `rpm`, `current_a`, `torque_nm`,
  `p_shaft_w`, `eta_motor`; torque derived as `P/(2π·n)`.
  - Legacy origin: `app/services/powertrain_performance.py:426`
  - Definition of done: a test asserts the stored `Torque_Nm` column is **not**
    read — patch it to an absurd value and assert the result is unchanged.
  - Confidence: 🟢

- [ ] **T-13 — RPM-group pre-filtering.**
  `compute_prop_operating_point`, `compute_performance_curve` and
  `_prop_torque_demand` filter the sample rows to the nearest RPM group before
  interpolating; the J-only helper merges all groups.
  - Legacy origin: `app/services/powertrain_performance.py`
  - Definition of done: a polar with 3000 / 6000 / 9000 rpm blocks and a
    computed 6100 rpm interpolates within the 6000 block. Document the tie-break
    for an exactly-equidistant RPM. 🟡
  - Confidence: 🟡

- [ ] **T-14 — The endpoint request schema and component resolution.**
  `PowertrainPerformanceEndpointRequest{motor_component_id,
  battery_component_id, propeller_polar_id, v_min_ms=0.0 (ge 0),
  v_max_ms=30.0 (gt 0), n_points=20 (1-200), altitude_m=0.0 (ge 0),
  throttle=1.0 (0 < t ≤ 1)}`; `_resolve_motor` / `_resolve_battery` /
  `_load_polar_rows` with their 404s and 422s.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/powertrain_performance.py`
  - Definition of done: a motor id pointing at a battery is 404; a motor without
    `kv_rpm_per_volt` is 422 **naming the component id and name**; a polar with
    no samples is 422. Reproduce the fact that these helpers raise
    `HTTPException` directly and record the layering break as a gap.
  - Confidence: 🟢

- [ ] **T-15 — The route.**
  `POST /aeroplanes/{aeroplane_id}/powertrain/performance`, 200,
  `operation_id=compute_powertrain_performance`, `aeroplane_id: UUID4`; 404 on
  an unknown aeroplane **even though no aeroplane data is read**.
  - Legacy origin: same file
  - Definition of done: a contract test asserts the 404-on-unknown-aeroplane
    behaviour explicitly, since it is otherwise indistinguishable from dead code.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Interpolation matrix:** in range · below `J_min` · above
      `J_max` (both clamped + flagged) · `Cp ≤ 0` ⇒ `Pe = 0` · `J = 0` ⇒
      `Pe = 0` · negative `Ct` ⇒ 0 · stored `Pe` ignored.
- [ ] **TT-02 — `output_kv`:** ungeared, 2:1 geared, `gear_ratio` absent, and
      `gear_ratio = 0` (treated as 1).
- [ ] **TT-03 — Pack voltage:** 3S ⇒ 11.1 V; a 4.2 V-per-cell variant differs by
      ~13 % (regression guard for BR-65).
- [ ] **TT-04 — Model A:** constant RPM across the sweep; `min()` ceiling
      respected at every point; `η_motor` default 0.85 when
      `efficiency_pct` is absent.
- [ ] **TT-05 — Model B:** monotonically falling RPM; bounded iterations;
      `η_motor ∈ [0,1]`; both bracket clamps.
- [ ] **TT-06 — Model selection:** `rm_ohm` present / absent / `0` — the last
      must select Model A.
- [ ] **TT-07 — Degenerate warnings:** zero RPM, unknown power limits,
      `P_shaft_max < 0.1 W` — each returns 200 with its exact text.
- [ ] **TT-08 — Sweep shape:** `n_points` samples, endpoints exact,
      `n_points = 1` legal.
- [ ] **TT-09 — Warning de-duplication:** an extrapolating sweep produces one
      warning, not one per point.
- [ ] **TT-10 — Torque provenance:** patch the stored `Torque_Nm` to an absurd
      value and assert the result is unchanged.
- [ ] **TT-11 — RPM-group filtering:** a 6100 rpm operating point uses the
      6000 rpm block.
- [ ] **TT-12 — Endpoint errors:** unknown aeroplane (404) · wrong component
      type (404) · missing motor KV (422) · missing `cells_lipo_max` (422) ·
      missing battery `cells` / `capacity_mah` (422) · empty polar (422).
- [ ] **TT-13 — Battery C-rate vocabulary (characterisation):** a battery whose
      specs carry only `c_rating` produces **no** battery power limit here; the
      test documents the gap.
- [ ] **TT-14 — Determinism:** two identical requests return byte-identical
      responses.
- [ ] **TT-15 — Fast-tier guard:** importing `powertrain_performance` must not
      import `aerosandbox` or `cadquery`.

## Data Migration Tasks

None. This use case reads existing rows and persists nothing. 🟢

The one indirect dependency is that a curve is reproducible **only** as long as
the polar snapshot version is pinned — see
[`../propeller-polars/tasks.md`](../propeller-polars/tasks.md) TM-01…TM-06.

## Suggested Order

1. **T-01 → T-03** — constants and the two spec schemas. Their derived
   properties (`output_kv`, `uses_qprop_model`, `nominal_voltage_v`) carry three
   of the use case's silent-error risks, so pin them first.
2. **T-04** next: the interpolation is a pure function over a sample list and is
   consumed by **both** models. It is the highest-value test surface in the use
   case.
3. **T-05** any time — independent of everything else.
4. **T-06** (Model A) before **T-07/T-08** (Model B): Model A is the shipped
   path, needs no solver, and its power ceiling logic is reused conceptually.
5. **T-07 → T-08** together — the bisection and its clamps are one unit; a
   clamp bug only shows up on degenerate brackets.
6. **T-09 → T-10** the selection flag and the warnings, which are what make both
   models honest.
7. **T-11 → T-13** the public entry points and the RPM filtering.
8. **T-14 → T-15** the endpoint last: it is a resolution shell over a service
   that is already fully tested.

## Pending Gaps (🔴)

- **Is the QPROP path reachable?** No seeded motor carries `rm_ohm`, so the
  refined model never runs in production. Should the catalogue be extended, or
  should Model A be documented as the product behaviour?
- **Which battery C-rate key wins** — `c_rate` (here), `c_rating` or
  `discharge_c` (the catalogue matchers)? Today a battery can silently lose its
  power limit.
- **Should windmilling drag be modelled?** `Ct` is clamped at 0, so descent and
  glide analyses built on these curves see zero propeller drag.
- **Should the module use `asb.Atmosphere`** instead of
  `1.225·exp(−h/8500)`, or is the divergence acceptable below a few hundred
  metres?
- **Should the endpoint helpers raise domain exceptions** instead of
  `HTTPException`, so the same failures are testable at the service layer?
- **Should a wrong component type be 422 rather than 404?** The id exists; it is
  simply the wrong kind of part.
- **What is the tie-break for an equidistant RPM group?** Undocumented today.
- **Should the router log its 500s?** It currently does not.
- **Should the aeroplane UUID be required at all**, given no aeroplane data is
  read?
</content>
