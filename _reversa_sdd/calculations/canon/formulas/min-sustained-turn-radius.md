---
canon: min-sustained-turn-radius
entry: formula
kind: optimization
tool: OPT
shape: law
status: draft
output: min-sustained-turn-radius, min-sustained-turn-radius-speed
source_status: NO_SOURCE_FOUND
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/no-source-found
  - dim/procedural
  - shape/law
  - kind/optimization
  - status/draft
tex: \begin{aligned}r_{min} = \min_{V,\,\alpha,\,n,\,n_{prop}}\; & \frac{V^2}{g\sqrt{n^2-1}} \\ \text{u.d.N.}\; & L(V,\alpha) = n\,m\,g \\ & T(V,n_{prop}) \ge D(V,\alpha) \\ & Q_m(n_{prop}) = Q_p(V,n_{prop}) \\ & 1 \le n \le n_{lim}\end{aligned}
inputs:
  airplane: airplane
  components: components
  m: aircraft-mass
  g: gravity
  rho: air-density
  n_lim: limit-load-factor
  k_v: motor-voltage-constant
  i_0: motor-no-load-current
  r_m: motor-circuit-resistance
  u_bat: battery-voltage
  p_mot_max: motor-max-power
  d_prop: propeller-diameter
  eta_mot: motor-efficiency
outputs: {r_min: min-sustained-turn-radius, v_r: min-sustained-turn-radius-speed}
embeds: [motor-propeller-equilibrium, advance-ratio-from-speed, propeller-table-lookup, thrust-at-airspeed-from-coefficient]
variables: [flight-speed]
optional: [r_m]
---

# Tightest sustained turn at full throttle

**Canonical form**

```
minimize over V, alpha, n, n_prop:   V^2 / (g * sqrt(n^2 - 1))
subject to:   L(V, alpha) = n * m * g
              T(V, n_prop) >= D(V, alpha)
              motor-propeller torque balance at (V, n_prop)
              1 <= n <= n_lim
```

**Produces** [[min-sustained-turn-radius]] · [[min-sustained-turn-radius-speed]]  ·  **from** [[airplane]] · [[components]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[limit-load-factor]] · [[motor-voltage-constant]] · [[motor-no-load-current]] · [[motor-circuit-resistance]] · [[battery-voltage]] · [[motor-max-power]] · [[propeller-diameter]] · [[motor-efficiency]]

**Kind: an optimisation problem**, the same shape as the extremal closures and the climb. Variables: airspeed `V`, angle of attack `alpha`, load factor `n`, propeller speed `n_prop`. A **sustained** turn: level, at constant speed, so thrust equals drag; the drag comes from AeroBuildup at the turn's `alpha`, so the induced drag of the higher lift is in it. Thrust and rpm as in the climb ([[motor-propeller-equilibrium]], route declared per `Q-PT-6`).

**Kinematics of the coordinated level turn.** `omega = g·sqrt(n² − 1) / V`, `r = V² / (g·sqrt(n² − 1))`; equivalently `n = 1/cos(phi)` (Lennon, *Basics of R/C Model Aircraft Design*, Ch. 21, as a vector sum of weight and centrifugal force). The bank angle is the result, not an input.

**Termination — which limit binds is the answer.** Three things can stop the turn, and the optimum says which:
- **thrust** — `T = D` binds, no bound active: the propulsion limits the turn;
- **the wing** — the optimum sits at the lift maximum of the polar: the aircraft can hold the turn only at the edge of stall;
- **the structure** — `n = n_lim` active: the turn is limited by the user's load limit, not by the aircraft's aerodynamics.

The last two are **declared active bounds**, named in the result like `gamma = 90°` in the climb. A failed solve returns no value (ADR 0020).

**Why not a bank angle as input.** A turn at a pilot-chosen bank angle says something about the pilot's choice, not about the aircraft. The stall speed in such a turn is the [[stall-speed]] problem with the load factor bound — one authority — which replaces `V_S,turn = V_S·sqrt(n)`: the shortcut assumes the straight-flight `C_L,max`, while the problem evaluates it at the turn's own Reynolds number. Both `turn-load-factor` and `stall-speed-in-turn` were deleted on 2026-10-01.

**Not here: the instantaneous turn.** Pulling beyond the sustained limit trades speed or height for a tighter turn, bounded by stall and structure. Its key number, the corner speed `V* = V_S·sqrt(n_lim)` — above it a full elevator input can break the aircraft — belongs to the flight envelope (§3.10, dive) and is noted there.

**Full throttle is a ceiling, not an equality** (corrected 2026-10-01 after the first run on BRYAN). The thrust constraint reads `T(V, n_prop) ≥ …`: the pilot can always throttle back. Written as an equality, an aircraft with a large thrust excess has no level or steady solution at low speed — on BRYAN half the problems failed and the "tightest turn" came out at 26 m/s. At the optimum the inequality binds wherever thrust is what limits.

**Source.** 🔴 NO SOURCE FOUND for the turn relation (below); the surrounding pieces are sourced. Load factor of the level turn as the vector sum of weight and centrifugal force, and the accelerated stall when the demanded C_L exceeds C_L,max: Lennon, *Basics of R/C Model Aircraft Design*, Ch. 21. Motor model: Drela `motor1` §1.1. 🔴 NO SOURCE FOUND for the radius `r = V²/(g·sqrt(n² − 1))` and rate `ω = g·sqrt(n² − 1)/V`: point-mass kinematics, with no equation reference in the Scholz/Sadraey, Anderson or AeroSandbox material.

**Validity in the RC/UAV regime (ADR 0028).** The kinematics are exact, with the load factor as the vector sum of weight and centrifugal force (Lennon, Ch. 21). The tightest sustained turn is flown slowly and at high `C_L`, so it sits at the lowest chord Reynolds number of manoeuvring flight — often in the bubble-sensitive band below 7·10⁴, where section C_L,max falls sharply (Lennon Ch. 1–3, see [[stall-speed]]). There the transition location sets the result: Anderson §20.3.2 shows laminar separation on both surfaces at Re_c = 10⁵ disappearing when the flow is turbulent. AeroBuildup does not claim accurate stall onset (AeroSandbox docs, AeroBuildup "Limitations"), and NeuralFoil's confidence drops near Re 8·10⁴, C_L 1.0 (Sharpe 2024 §7.2.4). Thrust at that low speed comes from the propeller table near static conditions, with its Re₀.₇₅ ≈ 15–100 k and rpm-block limits. Propeller slipstream over the wing is not modelled [no source].

## Implementations (0)

None in aero_kernel yet; no register node is mapped to this entry.

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
