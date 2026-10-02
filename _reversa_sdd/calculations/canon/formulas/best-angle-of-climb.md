---
canon: best-angle-of-climb
entry: formula
kind: optimization
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
tex: \begin{aligned}\gamma_{max} = \max_{V,\,\alpha,\,\gamma,\,n_{prop}}\; & \gamma \\ \text{u.d.N.}\; & L(V,\alpha) = m\,g\cos\gamma \\ & T(V,n_{prop}) - D(V,\alpha) \ge m\,g\sin\gamma \\ & Q_m(n_{prop}) = Q_p(V,n_{prop})\end{aligned}
---

# Best angle of climb at full throttle

**Canonical form**

```
maximize over V, alpha, gamma, n_prop:   gamma
subject to:   L(V, alpha) = m * g * cos(gamma)
              T(V, n_prop) - D(V, alpha) >= m * g * sin(gamma)
              motor-propeller torque balance at (V, n_prop)
```

**Produces** [[best-angle-of-climb-speed]] · [[max-climb-angle]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[thrust-at-airspeed]]

**Kind: an optimisation problem**, the same shape as the three extremal closures (§3.4.1). Variables: airspeed `V`, angle of attack `alpha`, flight-path angle `gamma`, propeller speed `n_prop`. AeroBuildup is inside the lift and drag constraints; the thrust is `T = C_T(J) · rho · n² · D⁴` ([[thrust-at-airspeed-from-coefficient]]) with the measured table of the fitted propeller; the rpm is tied to the motor by [[motor-propeller-equilibrium]] — as a constraint on route B; on route A the free-run rpm, lowered to the motor's power limit (O11).

**Exact steady climb, not the small-angle form.** Sadraey writes `ROC = (T − D)·V / W` with `L = W` (Eq. 4.84). That holds for shallow climbs only. A model with a high thrust-to-weight ratio climbs steeply, and with `T > W` vertically. Stating both force balances along and across the path costs one variable and keeps the result right at every angle; at `gamma = 90°` the lift constraint gives `L = 0`, which is the honest answer.

**Termination.** Approval asks for **no bound active at the optimum** — with one declared exception: `gamma` at its 90° bound means the aircraft climbs vertically at that speed. Any other active bound, and a failed solve, return no value (ADR 0020).

**The current is a verdict, not a constraint.** The optimum yields the motor current. Above the motor's, the controller's or the battery's limit the drive is overloaded at full throttle — reported, not optimised away.

**Model fidelity is declared** (`Q-PT-6`): which route of the torque balance ran, and that the battery voltage is nominal.

**Source.** 🟢 Sadraey §4.3.5 (rate and angle of climb, Eq. 4.84–4.85; angle of climb §4.3.5) for the definitions; the force balances are the steady-flight equations along and normal to the path. 🟢 Drela `motor1` §1.1 for the motor model.

**Replaces** `climb-speed-for-power-loading` (`V_climb = max(1.3·V_S,target, 1 m/s)`), deleted 2026-10-01: a multiple of a *target* stall speed, with neither thrust nor polar in it.

**Full throttle is a ceiling, not an equality** (corrected 2026-10-01 after the first run on BRYAN). The thrust constraint reads `T(V, n_prop) ≥ …`: the pilot can always throttle back. Written as an equality, an aircraft with a large thrust excess has no level or steady solution at low speed — on BRYAN half the problems failed and the "tightest turn" came out at 26 m/s. At the optimum the inequality binds wherever thrust is what limits.

**When the answer is vertical, `V_x` is not unique.** With thrust above weight the climb angle reaches 90° over a whole speed range (BRYAN: from about 3 m/s — hanging on the propeller). Then the result is "climbs vertically", with the range if wanted, and no single `V_x`.
