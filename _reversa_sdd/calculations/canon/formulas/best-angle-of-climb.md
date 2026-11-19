---
canon: best-angle-of-climb
entry: formula
kind: optimization
tool: OPT
shape: law
status: draft
output: best-angle-of-climb-speed, max-climb-angle
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/optimization
  - status/draft
tex: \begin{aligned}\gamma_{max} = \max_{V,\,\alpha,\,\gamma,\,n_{prop}}\; & \gamma \\ \text{u.d.N.}\; & L(V,\alpha) = m\,g\cos\gamma \\ & T(V,n_{prop}) - D(V,\alpha) \ge m\,g\sin\gamma \\ & Q_m(n_{prop}) = Q_p(V,n_{prop}) \\ & 0 \le \gamma \le \pi/2\end{aligned}
inputs:
  airplane: airplane
  components: components
  m: aircraft-mass
  g: gravity
  rho: air-density
  mu: dynamic-viscosity
  a: speed-of-sound
  k_v: motor-voltage-constant
  i_0: motor-no-load-current
  r_m: motor-circuit-resistance
  u_bat: battery-voltage
  p_mot_max: motor-max-power
  d_prop: propeller-diameter
  eta_mot: motor-efficiency
  v_s: stall-speed
outputs: {v_x: best-angle-of-climb-speed, gamma_max: max-climb-angle}
embeds: [motor-propeller-equilibrium, advance-ratio-from-speed, propeller-table-lookup, thrust-at-airspeed-from-coefficient]
variables: [flight-speed]
optional: [r_m, i_0]
preconditions:
  - {id: stall_speed_usable, parameter: v_s, on_violation: error}
---

# Best angle of climb at full throttle

**Canonical form**

```
maximize over V, alpha, gamma, n_prop:   gamma
subject to:   L(V, alpha) = m * g * cos(gamma)
              T(V, n_prop) - D(V, alpha) >= m * g * sin(gamma)
              motor-propeller torque balance at (V, n_prop)
              0 <= gamma <= pi/2
gamma in radians inside sin and cos; the output gamma_max = (180/pi) * gamma is in degrees
```

**Produces** [[best-angle-of-climb-speed]] · [[max-climb-angle]]  ·  **from** [[airplane]] · [[components]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[dynamic-viscosity]] · [[speed-of-sound]] · [[motor-voltage-constant]] · [[motor-no-load-current]] · [[motor-circuit-resistance]] · [[battery-voltage]] · [[motor-max-power]] · [[propeller-diameter]] · [[motor-efficiency]] · [[stall-speed]]

**Kind: an optimisation problem**, the same shape as the three extremal closures (§3.4.1). Variables: airspeed `V`, angle of attack `alpha`, flight-path angle `gamma`, propeller speed `n_prop`. AeroBuildup is inside the lift and drag constraints; the thrust is `T = C_T(J) · rho · n_prop² · D_prop⁴` ([[thrust-at-airspeed-from-coefficient]]) with the measured table of the fitted propeller; the rpm is tied to the motor by [[motor-propeller-equilibrium]] — as a constraint on route B; on route A the free-run rpm, lowered to the motor's power limit (O11).

**Exact steady climb, not the small-angle form.** Sadraey writes `ROC = (T·V − D·V) / W` with `L = W` (Eq. 4.77–4.78, §4.3.5; the propeller form `(η_P·P − D·V)/W` is Eq. 4.84, §4.3.5.2). That holds for shallow climbs only. A model with a high thrust-to-weight ratio climbs steeply, and with `T > W` vertically. Stating both force balances along and across the path costs one variable and keeps the result right at every angle; at `gamma = 90°` the lift constraint gives `L = 0`, which is the honest answer.

**Termination.** The bound `0 ≤ γ ≤ π/2` is part of the problem: without it the inverted solution `γ = π` (`L = −m·g`, `T ≥ D`) would be feasible and larger than any upright climb angle; `sin` and `cos` are periodic, so without the bound the problem is unbounded in `γ` and has no maximum. `γ` is in radians inside `sin` and `cos` and is converted to degrees for the output. Approval asks for **no bound active at the optimum** — with one declared exception: `gamma` at its 90° bound means the aircraft climbs vertically at that speed. Any other active bound, and a failed solve, return no value (ADR 0020).

**Remark on Termination (#1414).** An optimum on the stall corner is returned together with the notice `powered_limit_declared` (`limit` `wing`) instead of being withheld; reasons as in `best-rate-of-climb`: the best angle of climb sits on or within 1 % of the stall corner on every airplane measured (closed-form airplane at 3.4 and 6.0 kg; Avistar Elite `V_x` 10.0 m/s at 40.6 deg with `C_L` 1.19 against 1.22 at the stall).

**The current is a verdict, not a constraint.** The optimum yields the motor current. Above the motor's, the controller's or the battery's limit the drive is overloaded at full throttle — reported, not optimised away.

**Model fidelity is declared** (`Q-PT-6`): which route of the torque balance ran, and that the battery voltage is nominal.

**Source.** 🟢 Sadraey §4.3.5 (rate of climb, Eq. 4.77–4.78; propeller form Eq. 4.84–4.85, §4.3.5.2) for the definitions — no explicit Sadraey angle-of-climb equation was found; the force balances along and normal to the path, with the small-angle form only for γ < 15°: Scholz 05_PreliminarySizing §5.3 (context of Eq. 5.13). 🟢 Drela `motor1` §1.1 for the motor model.

**Validity in the RC/UAV regime (ADR 0028).** The force balances are exact steady-flight equations at any climb angle: Scholz states them along and normal to the path and uses `L ≈ m·g` only "for γ < 15°" (05_PreliminarySizing §5.3), so keeping both balances is what makes the result right for steep and vertical RC climbs. Thrust inherits the propeller-table and motor-model limits (Re₀.₇₅ ≈ 15–100 k per rpm block, nominal battery voltage, route A rpm). The optimum lies at low speed and high `C_L`, so the result depends on the polar near its maximum: AeroBuildup does not claim accurate stall onset (AeroSandbox docs, AeroBuildup "Limitations"), and near Re 8·10⁴ and C_L 1.0 NeuralFoil's confidence drops (Sharpe 2024 §7.2.4). Propeller slipstream over wing and tail is not in AeroBuildup [no source]; it matters most at full throttle and low speed.

**Replaces** `climb-speed-for-power-loading` (`V_climb = max(1.3·V_S,target, 1 m/s)`), deleted 2026-10-01: a multiple of a *target* stall speed, with neither thrust nor polar in it.

**Full throttle is a ceiling, not an equality** (corrected 2026-10-01 after the first run on BRYAN). The thrust constraint reads `T(V, n_prop) ≥ …`: the pilot can always throttle back. Written as an equality, an aircraft with a large thrust excess has no level or steady solution at low speed — on BRYAN half the problems failed and the "tightest turn" came out at 26 m/s. At the optimum the inequality binds wherever thrust is what limits.

**When the answer is vertical, `V_x` is not unique.** With thrust above weight the climb angle reaches 90° over a whole speed range (BRYAN: from about 3 m/s — hanging on the propeller). Then the result is "climbs vertically", with the range if wanted, and no single `V_x`.

**Remark (gh-1419, undated):** the scan of the speed starts at a speed tied to the airplane, not at a fixed 2 m/s: the clean stall speed is read as the input `v_s` <- [[stall-speed]] (application `clean`; the same reading as in [[endurance-and-range-optimum]], one producer, ADR 0022). At a speed far below the stall speed the solver adapter's angle sweep can show no lift peak (very low Reynolds number); that is a failure of the solver, not a stall, and it ended the formula at a speed the aircraft cannot fly. A climb at the angle `gamma` carries `m g cos(gamma)` and can be flown down to `v_s sqrt(cos gamma)`. The steepest angle the drive train can hold is `sin gamma_T = T_0 / (m g)` with `T_0` the thrust at no airspeed (the largest it gives), so the scan starts at `v_s (1 - (T_0 / m g)^2)^(1/4)`; the best angle may therefore lie below the level stall speed (the Avistar Elite: 10.0 m/s against 11.4 m/s). Where that is below `powered_climb_scan_floor` of `v_s` the scan starts at the floor, a constant chosen by the implementer without a source (`config.yaml`), declared with the answer (`powered_limit_declared`, limit `scan_floor`). The static thrust `T_0` is the drive train's thrust at `J = 0`; a propeller table without that point gives no `T_0`, and the climb scan starts at the floor (declared, `powered_limit_declared`, limit `scan_floor`). Where the drive train gives more thrust than `T_0` at some speed the bound `T_0` is not the largest, the start may have been too high, and the notice `powered_limit_declared` (limit `static_thrust_not_largest`) says so. The input `v_s` has the precondition `stall_speed_usable` (positive, finite, at most the scan limit).

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| `aero_kernel/formulas/best_angle_of_climb.py` | DEVIATES | 🟢 | per speed the steepest steady climb angle (as `best-rate-of-climb`), then the maximum of `gamma` over the speed. The vertical case returns `gamma = 90 deg` at the upper edge of the speed range in which the climb is vertical (the entry: no single `V_x`), declared by the notice `powered_limit_declared`. **Deviation:** the entry's optimisation is solved by what it reduces to: `alpha` (lift equals `n m g`) and `n_prop` (torque balance) are eliminated by the kernel's two existing solves (`OptiAdapter.level_flight_point` with a load factor, and `full_throttle_thrust`, the composition of the four embedded relations), leaving a one-dimensional search over `V`. The torque balance is a bisection on the propeller table and cannot enter an IPOPT problem, so no IPOPT problem is posed. The numerical settings are `powered_*` in `config.yaml`. Route B only (a missing `R_m`, `I_0` or propeller table is `missing_input`); the speed beyond the propeller table is the declared failure `outside_propeller_table` (no extrapolation). Warnings of the iterates are not forwarded, only those of the answer. |

No register node is mapped to this entry.

**Implementation note (gh-1414).** The optimum of the angle of climb lies on, or within 1 % of, the stall corner: on a closed-form airplane with a thrust-to-weight ratio near 1 the steepest angle is flown at the lowest speed at which the wing still carries `m g cos gamma`; on the Avistar Elite (AXI 4120/14 on 4S, APC 13x8E) `V_x` is 10.0 m/s at 40.6 deg, below the level-flight stall speed of 11.4 m/s because a steep path needs less lift, at `C_L` 1.19 against 1.22 at the stall. A corner optimum is returned with the notice `powered_limit_declared` (`limit` `wing`), not withheld; see #1414 (the entry's Termination text asks for no value there; see the remark on Termination).

**Implementation remark on method and assumptions (#1414).** As `best-rate-of-climb`, with the angle itself as the objective. Assumptions: one maximum of the angle over the speed; one root of the excess over the angles the wing can carry; features no narrower than the scan step (2 m/s).

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [ ] **Relation and method** — which equation it solves, and by which named method
- [ ] **Assumptions** — the conditions the method requires (bracketing, continuity, range)
- [ ] **Convergence** — the criterion, and what is returned and declared on failure
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.
