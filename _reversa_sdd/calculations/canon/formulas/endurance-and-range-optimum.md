---
canon: endurance-and-range-optimum
entry: formula
kind: optimization
tool: OPT
shape: law
status: draft
output: max-endurance, max-range
source_status: PARTIAL
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/partial
  - dim/procedural
  - shape/law
  - kind/optimization
  - status/draft
tex: \begin{aligned}t_{max} = \frac{3600\,E_{bat}}{\min_V P_{bat}(V)}, \quad R_{max} = \frac{3600\,E_{bat}}{\min_V P_{bat}(V)/V}\end{aligned}
inputs:
  airplane: airplane
  m: aircraft-mass
  g: gravity
  rho: air-density
  e_bat: battery-capacity
  mu: dynamic-viscosity
  a: speed-of-sound
  components: components
  k_v: motor-voltage-constant
  i_0: motor-no-load-current
  r_m: motor-circuit-resistance
  u_bat: battery-voltage
  p_mot_max: motor-max-power
  d_prop: propeller-diameter
  eta_mot: motor-efficiency
outputs: {t_max: max-endurance, r_max: max-range}
embeds: [motor-propeller-part-load, stall-speed.clean]
variables: [flight-speed]
optional: [r_m, i_0]
---

# Greatest endurance and greatest range — the optimised values

**Canonical form**

```
minimize over V:   P_bat(V)            subject to  V >= V_S,  r_T(V) <= 1       ->  t_max = 3600 * E_bat / P_bat*
minimize over V:   P_bat(V) / V        subject to  V >= V_S,  r_T(V) <= 1       ->  R_max = 3600 * E_bat / (P_bat/V)*
P_bat(V), r_T(V) := battery-power, thrust-demand-ratio of motor-propeller-part-load at V
V_S              := stall speed of stall-speed.clean
```

**Produces** [[max-endurance]] · [[max-range]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[battery-capacity]] · [[dynamic-viscosity]] · [[speed-of-sound]] · [[components]] · [[motor-voltage-constant]] · [[motor-no-load-current]] · [[motor-circuit-resistance]] · [[battery-voltage]] · [[motor-max-power]] · [[propeller-diameter]] · [[motor-efficiency]]

**Kind: an optimisation problem.** The speed is not given but found: the one at which the **battery power** of the part-load chain is least (endurance) or the battery energy per metre `P_bat/V` is least (range). The domain is the speeds the airplane can fly level — from the stall speed up to where the required thrust reaches the full-throttle thrust (`r_T ≤ 1`, [[thrust-demand-ratio]]). This is the **optimised** value of decision 2 (maintainer, 2026-10-25, #1235); [[endurance-and-range]] gives the estimate at `V_mp` and `V_md`, which does not exceed it where its speeds lie inside the domain. Approval asks, on top of source and scale: **no bound active at the optimum** (an optimum at `V_S` or at `r_T = 1` is reported, not accepted silently) and **what is returned when the solver fails** — never a value.

**Ist ≠ Soll (#1235).** Ist: `app/services/endurance_service.py` converts aerodynamic power to battery power with one constant, η ≈ 0.52 (η_prop 0.65 × η_motor 0.85 × η_ESC 0.94, all assumptions). Soll: the app **must follow** this entry and take the battery power from the part-load chain (follow-up of #1235; the ticket number is added by the orchestrator).

**Source.** 🟡 PARTIAL. As in [[endurance-and-range]]: the energy balance `t = E_bat/P_bat`, `R = V·t` has no textbook source [no source]; Sadraey's closures (§4.2.5.2 Eq. 4.17, §4.2.5.4 Eq. 4.22–4.23) are the constant-`η_P` special case, in which the optima fall at `V_md` and `V_mp`.

**Validity in the RC/UAV regime (ADR 0028).** The optimum moves with the propeller's efficiency curve, which at Re₀.₇₅ ≈ 15–100 k depends strongly on advance ratio and Reynolds number (Brandt & Selig 2011 §IV; Deters, Ananda & Selig 2014 §V.A–B), and the lowest speeds of the domain sit at high `C_L`, where the low-Re polar is least certain (Sharpe 2024 §7.2.4). Battery sag, the usable fraction of the charge and reserve are not modelled [no source]; the battery is taken as its full rated energy. Mach is no concern (Anderson §1.10.3).

## Implementations (0)

None in aero_kernel yet; no register node is mapped to this entry (kernel implementation of the part-load chain and the optimisation: follow-up of #1235).

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
