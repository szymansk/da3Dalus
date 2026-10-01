---
canon: best-rate-of-climb
entry: formula
kind: optimization
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
tex: \begin{aligned}\mathit{ROC}_{max} = \max_{V,\,\alpha,\,\gamma,\,n}\; & V\sin\gamma \\ \text{u.d.N.}\; & L(V,\alpha) = m\,g\cos\gamma \\ & T(V,n) - D(V,\alpha) = m\,g\sin\gamma \\ & Q_m(n) = Q_p(V,n)\end{aligned}
---

# Best rate of climb at full throttle

**Canonical form**

```
maximize over V, alpha, gamma, n:   V * sin(gamma)
subject to:   L(V, alpha) = m * g * cos(gamma)
              T(V, n) - D(V, alpha) = m * g * sin(gamma)
              motor-propeller torque balance at (V, n)
```

**Produces** [[best-rate-of-climb-speed]] · [[max-rate-of-climb]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[motor-voltage-constant]] · [[motor-no-load-current]] · [[motor-circuit-resistance]] · [[battery-voltage]]

**Kind: an optimisation problem**, the same shape as the three extremal closures (§3.4.1). Variables: airspeed `V`, angle of attack `alpha`, flight-path angle `gamma`, propeller speed `n`. AeroBuildup is inside the lift and drag constraints; the thrust is `T = C_T(J) · rho · n² · D⁴` ([[thrust-at-airspeed-from-coefficient]]) with the measured table of the fitted propeller; the rpm is tied to the motor by [[motor-propeller-equilibrium]] — as a constraint on route B, as a fixed value on route A.

**Exact steady climb, not the small-angle form.** Sadraey writes `ROC = (T − D)·V / W` with `L = W` (Eq. 4.84). That holds for shallow climbs only. A model with a high thrust-to-weight ratio climbs steeply, and with `T > W` vertically. Stating both force balances along and across the path costs one variable and keeps the result right at every angle; at `gamma = 90°` the lift constraint gives `L = 0`, which is the honest answer.

**Termination.** Approval asks for **no bound active at the optimum** — with one declared exception: `gamma` at its 90° bound means the aircraft climbs vertically at that speed. Any other active bound, and a failed solve, return no value (ADR 0020).

**The current is a verdict, not a constraint.** The optimum yields the motor current. Above the motor's, the controller's or the battery's limit the drive is overloaded at full throttle — reported, not optimised away.

**Model fidelity is declared** (`Q-PT-6`): which route of the torque balance ran, and that the battery voltage is nominal.

**Source.** 🟢 Sadraey §4.3.5 (rate and angle of climb, Eq. 4.84–4.85) for the definitions; the force balances are the steady-flight equations along and normal to the path. 🟢 Drela `motor1` §1.1 for the motor model.

**Replaces** `climb-speed-for-power-loading` (`V_climb = max(1.3·V_S,target, 1 m/s)`), deleted 2026-10-01: a multiple of a *target* stall speed, with neither thrust nor polar in it.
