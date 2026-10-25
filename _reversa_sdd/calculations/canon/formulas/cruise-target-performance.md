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
  v_cruise_target: cruise-speed-target
  components: components
  k_v: motor-voltage-constant
  i_0: motor-no-load-current
  r_m: motor-circuit-resistance
  u_bat: battery-voltage
  p_mot_max: motor-max-power
  d_prop: propeller-diameter
  eta_mot: motor-efficiency
outputs: {t_cruise: endurance-at-cruise-target, r_cruise: range-at-cruise-target}
applications:
  - id: at_cruise_speed_target
    given: [cruise-speed-target]
embeds: [motor-propeller-part-load]
variables: [flight-speed]
optional: [r_m, i_0]
---

# Endurance and range at the mission's cruise speed

**Canonical form**

```
P_bat := battery-power of motor-propeller-part-load at V_cruise,target   (thrust = drag, level flight)
t_cruise = 3600 * E_bat / P_bat
R_cruise = V_cruise,target * t_cruise
```

**Produces** [[endurance-at-cruise-target]] · [[range-at-cruise-target]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[battery-capacity]] · [[cruise-speed-target]] · [[components]] · [[motor-voltage-constant]] · [[motor-no-load-current]] · [[motor-circuit-resistance]] · [[battery-voltage]] · [[motor-max-power]] · [[propeller-diameter]] · [[motor-efficiency]]

**Kind: a procedure — the part-load chain at a named speed.** At the target speed the battery power
comes from [[motor-propeller-part-load]] (level-flight `α` from `L = m·g`, drag from the solver — ADR 0026
— thrust = drag, motor model, propeller table). Endurance `t = 3600·E_bat/P_bat`; range `R = V·t`. Both
factors of the range come from the **same** speed — the precondition §3.5 named. **No assumed
drive-train efficiency** (maintainer, 2026-10-25, #1235): the former `propulsive-efficiency` is deleted
(ADR 0021).

**Declared simplifications.** The battery is taken as its full rated energy, no voltage sag, no reserve.
If the thrust required at the target speed exceeds the full-throttle thrust, [[thrust-demand-ratio]] of
the embedded entry is above 1 and the part-load entry warns; the target speed cannot be held.

**Ist ≠ Soll (#1235).** Ist: `app/services/endurance_service.py` uses one constant, η ≈ 0.52 (η_prop 0.65 × η_motor 0.85 × η_ESC 0.94, all assumptions). Soll: the app **must follow** this entry (#1238).

**Measured against a target.** A UAV mission often prescribes its cruise speed (area coverage per
time, wind penetration). This entry answers *how long and how far at that speed* — the UAV purpose
names cruise speed explicitly. Not a pilot's choice as a closure (§3.5): the speed is a mission
requirement, the result is measured against it (A9).

**Source.** 🟡 PARTIAL. The battery-electric form has no textbook source; its pieces are elementary: `t = E_bat/P_bat`, `R = V·t` [no source], with the battery power of [[motor-propeller-part-load]]. Sadraey gives only the fuel-burning Breguet forms for propeller aircraft (§4.2.5.2, Eq. 4.17; §4.2.5.4, Eq. 4.23). Electric propulsion appears in Sadraey only descriptively (§8.3.1). The cruise speed is a mission input, not a closure.

**Validity in the RC/UAV regime (ADR 0028).** The energy balance is regime-independent; drag and propulsive efficiency carry the regime. Model-scale profile drag is Reynolds- and transition-sensitive (Anderson §4.12; Lennon Ch. 1–3). If the target speed lies near the stall, the wing works near `C_L ≈ 1`, where NeuralFoil flags a laminar separation bubble and low confidence at `Re_c ≈ 8·10⁴` (Sharpe 2024 §7.2.4). The drive-train side is as valid as [[motor-propeller-part-load]]: small-propeller efficiency spans 0.28–0.65 across designs and falls below a blade Re of about 10⁵ (Brandt & Selig 2011 §IV), which the propeller table carries instead of one constant. Usable battery fraction, voltage sag and reserve are not modelled [no source]. Mach is no concern (Anderson §1.10.3).

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
