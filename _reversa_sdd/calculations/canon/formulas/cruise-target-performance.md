---
canon: cruise-target-performance
entry: formula
kind: procedure
tool: OPT
shape: law
status: draft
output: endurance-at-cruise-target, range-at-cruise-target
source_status: PARTIAL
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/partial
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
inputs:
  airplane: airplane
  m: aircraft-mass
  g: gravity
  rho: air-density
  e_bat: battery-capacity
  eta: propulsive-efficiency
  v_cruise_target: cruise-speed-target
outputs: {t_cruise: endurance-at-cruise-target, r_cruise: range-at-cruise-target}
applications:
  - id: at_cruise_speed_target
    given: [cruise-speed-target]
---

# Endurance and range at the mission's cruise speed

**Canonical form**

```
solve for alpha at V_cruise,target:   L = m * g
t_cruise = 3600 * E_bat * eta / ( D(V_cruise,target) * V_cruise,target )
R_cruise = 3600 * E_bat * eta / D(V_cruise,target)
```

**Produces** [[endurance-at-cruise-target]] · [[range-at-cruise-target]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[battery-capacity]] · [[propulsive-efficiency]] · [[cruise-speed-target]]

**Kind: a procedure — the solver at a named speed.** At the target speed the level-flight `α` is solved
from `L = m·g` (AeroBuildup), the drag `D` taken from the solver (ADR 0026). Power required is
`P = D·V/η`; endurance `t = 3600·E_bat/P`; range `R = V·t = 3600·η·E_bat/D` — so range is largest
where drag is smallest (`V_md`) and endurance where power is smallest (`V_mp`) (§3.5: two closures,
not three). Both factors of the range come from the **same** speed — the precondition §3.5 named.

**Declared simplifications.** `η` is one number for the whole drive train (`propulsive-efficiency`),
although the propeller's efficiency varies with the advance ratio; the battery is taken as its
usable energy, no voltage sag, no reserve.

**Measured against a target.** A UAV mission often prescribes its cruise speed (area coverage per
time, wind penetration). This entry answers *how long and how far at that speed* — the UAV purpose
names cruise speed explicitly. Not a pilot's choice as a closure (§3.5): the speed is a mission
requirement, the result is measured against it (A9).

**Source.** 🟡 PARTIAL. The battery-electric form has no textbook source; its pieces are elementary: `P = D·V/η`, `t = E_bat/P`, `R = V·t` [no source]. Sadraey gives only the fuel-burning Breguet forms for propeller aircraft (§4.2.5.2, Eq. 4.17; §4.2.5.4, Eq. 4.23); with constant mass, as for a battery, they reduce to the same dependence on `η_P·L/D`. Electric propulsion appears in Sadraey only descriptively (§8.3.1). The cruise speed is a mission input, not a closure.

**Validity in the RC/UAV regime (ADR 0028).** The energy balance is regime-independent; drag and propulsive efficiency carry the regime. Model-scale profile drag is Reynolds- and transition-sensitive (Anderson §4.12; Lennon Ch. 1–3). If the target speed lies near the stall, the wing works near `C_L ≈ 1`, where NeuralFoil flags a laminar separation bubble and low confidence at `Re_c ≈ 8·10⁴` (Sharpe 2024 §7.2.4). The single `η` is the dominant declared simplification: small-propeller efficiency spans 0.28–0.65 across designs and falls below a blade Re of about 10⁵ (Brandt & Selig 2011 §IV). Usable battery fraction, voltage sag and reserve are not modelled [no source]. Mach is no concern (Anderson §1.10.3).

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
