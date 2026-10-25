---
canon: max-level-speed
entry: formula
kind: optimization
tool: OPT
shape: law
status: draft
output: max-level-speed
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/optimization
  - status/draft
tex: \begin{aligned}V_{max} = \max_{V,\,\alpha,\,n_{prop}}\; & V \\ \text{u.d.N.}\; & L(V,\alpha) = m\,g \\ & T(V,n_{prop}) \ge D(V,\alpha) \\ & Q_m(n_{prop}) = Q_p(V,n_{prop})\end{aligned}
inputs:
  airplane: airplane
  components: components
  m: aircraft-mass
  g: gravity
  rho: air-density
  k_v: motor-voltage-constant
  i_0: motor-no-load-current
  r_m: motor-circuit-resistance
  u_bat: battery-voltage
  p_mot_max: motor-max-power
  d_prop: propeller-diameter
  eta_mot: motor-efficiency
outputs: {v_max: max-level-speed}
embeds: [motor-propeller-equilibrium, advance-ratio-from-speed, propeller-table-lookup, thrust-at-airspeed-from-coefficient]
variables: [flight-speed]
optional: [r_m, i_0]
---

# Maximum level speed at full throttle

**Canonical form**

```
maximize over V, alpha, n_prop:   V
subject to:   L(V, alpha) = m * g
              T(V, n_prop) >= D(V, alpha)
              motor-propeller torque balance at (V, n_prop)
```

**Produces** [[max-level-speed]]  ·  **from** [[airplane]] · [[components]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[motor-voltage-constant]] · [[motor-no-load-current]] · [[motor-circuit-resistance]] · [[battery-voltage]] · [[motor-max-power]] · [[propeller-diameter]] · [[motor-efficiency]]

**Kind: an optimisation problem**, the same shape as climb and turn: the highest speed at which full-throttle thrust still equals drag in level flight. Thrust and rpm from [[motor-propeller-equilibrium]] (route declared, `Q-PT-6`).

**Source.** 🟢 Sadraey §4.3.3.2, Eq. 4.50 — maximum speed of a propeller aircraft where available power equals required power (`η_P·P_max = T·V_max`), equivalent to thrust available equals thrust required.

**Validity in the RC/UAV regime (ADR 0028).** The closure, available power equal to required power, is regime-independent; Sadraey writes it with one constant `η_P` (§4.3.3.2, Eq. 4.50), where this entry uses the propeller table. At `V_max` the lift coefficient is small and drag is mostly profile drag, which depends on transition and hence on the chord Reynolds number (Anderson §4.12); Lennon (Ch. 1–3) reports it nearly doubling at low model Rn. Small-propeller efficiency spans 0.28–0.65 across designs and degrades below a blade Re of about 10⁵ (Brandt & Selig 2011 §IV). AeroBuildup's post-stall values are "order-of-magnitude correct rather than highly accurate" (AeroSandbox tutorial, AeroBuildup overview), which is why the spurious post-stall branch needs the multi-start rule. The incompressible solver is exact while `V_max` stays below M ≈ 0.3 (Anderson §1.10.3).

**Was an input until 2026-10-01** — "maximum level-flight speed goal, defaulting to 28 m/s", the same for every aircraft. A computed property now. A *goal* for the maximum speed, if a mission needs one, is a requirement compared against this value in the Probe, not a substitute for it.

**Termination.** No bound active at the optimum; a failed solve returns no value (ADR 0020). If the thrust runs past the propeller's zero-thrust advance ratio first, the propeller — not the drag — limits the speed, and that is named.

**Full throttle is a ceiling, not an equality** (corrected 2026-10-01 after the first run on BRYAN). The thrust constraint reads `T(V, n_prop) ≥ …`: the pilot can always throttle back. Written as an equality, an aircraft with a large thrust excess has no level or steady solution at low speed — on BRYAN half the problems failed and the "tightest turn" came out at 26 m/s. At the optimum the inequality binds wherever thrust is what limits.

**Multi-start.** The problem has a spurious branch below the stall, where the polar's post-stall drag rise also satisfies `T ≥ D`; on BRYAN one start converged there (5.9 m/s at α = 16.7°). Solve from several starting speeds and keep the largest feasible `V` with no stall-side bound active.

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
