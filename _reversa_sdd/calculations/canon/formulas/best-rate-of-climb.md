---
canon: best-rate-of-climb
entry: formula
kind: optimization
tool: OPT
shape: law
status: draft
output: best-rate-of-climb-speed, max-rate-of-climb
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/optimization
  - status/draft
tex: \begin{aligned}\mathit{ROC}_{max} = \max_{V,\,\alpha,\,\gamma,\,n_{prop}}\; & V\sin\gamma \\ \text{u.d.N.}\; & L(V,\alpha) = m\,g\cos\gamma \\ & T(V,n_{prop}) - D(V,\alpha) \ge m\,g\sin\gamma \\ & Q_m(n_{prop}) = Q_p(V,n_{prop}) \\ & 0 \le \gamma \le \pi/2\end{aligned}
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
outputs: {v_y: best-rate-of-climb-speed, roc_max: max-rate-of-climb}
embeds: [motor-propeller-equilibrium, advance-ratio-from-speed, propeller-table-lookup, thrust-at-airspeed-from-coefficient]
variables: [flight-speed]
optional: [r_m, i_0]
---

# Best rate of climb at full throttle

**Canonical form**

```
maximize over V, alpha, gamma, n_prop:   V * sin(gamma)
subject to:   L(V, alpha) = m * g * cos(gamma)
              T(V, n_prop) - D(V, alpha) >= m * g * sin(gamma)
              motor-propeller torque balance at (V, n_prop)
              0 <= gamma <= pi/2
gamma in radians inside sin and cos; where it is reported, it is converted to degrees, (180/pi) * gamma
```

**Produces** [[best-rate-of-climb-speed]] · [[max-rate-of-climb]]  ·  **from** [[airplane]] · [[components]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[dynamic-viscosity]] · [[speed-of-sound]] · [[motor-voltage-constant]] · [[motor-no-load-current]] · [[motor-circuit-resistance]] · [[battery-voltage]] · [[motor-max-power]] · [[propeller-diameter]] · [[motor-efficiency]]

**Kind: an optimisation problem**, the same shape as the three extremal closures (§3.4.1). Variables: airspeed `V`, angle of attack `alpha`, flight-path angle `gamma`, propeller speed `n_prop`. AeroBuildup is inside the lift and drag constraints; the thrust is `T = C_T(J) · rho · n_prop² · D_prop⁴` ([[thrust-at-airspeed-from-coefficient]]) with the measured table of the fitted propeller; the rpm is tied to the motor by [[motor-propeller-equilibrium]] — as a constraint on route B; on route A the free-run rpm, lowered to the motor's power limit (O11).

**Exact steady climb, not the small-angle form.** Sadraey writes `ROC = (T·V − D·V) / W` with `L = W` (Eq. 4.77–4.78, §4.3.5; the propeller form `(η_P·P − D·V)/W` is Eq. 4.84, §4.3.5.2). That holds for shallow climbs only. A model with a high thrust-to-weight ratio climbs steeply, and with `T > W` vertically. Stating both force balances along and across the path costs one variable and keeps the result right at every angle; at `gamma = 90°` the lift constraint gives `L = 0`, which is the honest answer.

**Termination.** The bound `0 ≤ γ ≤ π/2` is part of the problem: without it every upright climb `γ` has a mirrored inverted twin `γ' = π − γ` in `(π/2, π]` — the same `sin γ`, `cos γ' = −cos γ`, hence `L = −m·g·cos γ` — which is feasible with the same objective value `V·sin γ`, so the optimum would not be unique. `γ` is in radians inside `sin` and `cos`; this entry outputs no angle, and where `γ` is reported it is converted to degrees. Approval asks for **no bound active at the optimum** — with one declared exception: `gamma` at its 90° bound means the aircraft climbs vertically at that speed. Any other active bound, and a failed solve, return no value (ADR 0020).

**The current is a verdict, not a constraint.** The optimum yields the motor current. Above the motor's, the controller's or the battery's limit the drive is overloaded at full throttle — reported, not optimised away.

**Model fidelity is declared** (`Q-PT-6`): which route of the torque balance ran, and that the battery voltage is nominal.

**Source.** 🟢 Sadraey §4.3.5 (rate of climb, Eq. 4.77–4.78; propeller form Eq. 4.84–4.85, §4.3.5.2) for the definitions; the force balances along and normal to the path, with the small-angle form only for γ < 15°: Scholz 05_PreliminarySizing §5.3 (context of Eq. 5.13). 🟢 Drela `motor1` §1.1 for the motor model.

**Validity in the RC/UAV regime (ADR 0028).** The force balances are exact at any climb angle; Scholz uses the small-angle form only for γ < 15° (05_PreliminarySizing §5.3), and the entry does not use it. Sadraey's closed form puts the propeller optimum at the minimum-power speed with a constant `η_P` of 0.5–0.6 for fixed pitch (§4.3.5.2, Eq. 4.84–4.85); this entry replaces both with the propeller table and the motor balance, so it carries no fixed-efficiency assumption. Thrust inherits that chain's limits: the coefficients depend on the propeller's Re₀.₇₅ ≈ 15–100 k (ADR 0028; Deters, Ananda & Selig 2014 §V.A–B), with nominal battery voltage and route A free-run rpm. The optimum lies at moderate `C_L`, usually away from the stall corner, so polar uncertainty near C_L,max matters less than for `V_x` [no source]. Propeller slipstream is not modelled [no source].

**Replaces** `climb-speed-for-power-loading` (`V_climb = max(1.3·V_S,target, 1 m/s)`), deleted 2026-10-01: a multiple of a *target* stall speed, with neither thrust nor polar in it.

**Full throttle is a ceiling, not an equality** (corrected 2026-10-01 after the first run on BRYAN). The thrust constraint reads `T(V, n_prop) ≥ …`: the pilot can always throttle back. Written as an equality, an aircraft with a large thrust excess has no level or steady solution at low speed — on BRYAN half the problems failed and the "tightest turn" came out at 26 m/s. At the optimum the inequality binds wherever thrust is what limits.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| `aero_kernel/formulas/best_rate_of_climb.py` | DEVIATES | 🟢 | per speed the steepest steady climb angle (root of `T - D(V, cos gamma) - m g sin gamma` on the angles the wing can carry, vertical where the excess at 90 deg is not negative), then the maximum of `V sin gamma` over the speed (scan and golden section). **Deviation:** the entry's optimisation is solved by what it reduces to: `alpha` (lift equals `n m g`) and `n_prop` (torque balance) are eliminated by the kernel's two existing solves (`OptiAdapter.level_flight_point` with a load factor, and `full_throttle_thrust`, the composition of the four embedded relations), leaving a one-dimensional search over `V`. The torque balance is a bisection on the propeller table and cannot enter an IPOPT problem, so no IPOPT problem is posed. The numerical settings are `powered_*` in `config.yaml`. Route B only (a missing `R_m`, `I_0` or propeller table is `missing_input`); the speed beyond the propeller table is the declared failure `outside_propeller_table` (no extrapolation). Warnings of the iterates are not forwarded, only those of the answer. |

No register node is mapped to this entry.

**Implementation note (gh-1414).** The optimum at the stall corner is returned with the notice `powered_limit_declared` (`limit` `wing`), not withheld; see the decision file `climb-optimum-on-the-stall-corner` (the entry's Termination text asks for no value there; the sibling decision of #1268 for `minimum-sink-speed` returns the boundary value with a notice).

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
