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
  v_s: stall-speed
outputs: {t_max: max-endurance, r_max: max-range}
embeds: [motor-propeller-part-load]
variables: [flight-speed]
optional: [r_m, i_0]
---

# Greatest endurance and greatest range — the optimised values

**Canonical form**

```
minimize over V:   P_bat(V)            subject to  V >= V_S,  r_T(V) <= 1       ->  t_max = 3600 * E_bat / P_bat*
minimize over V:   P_bat(V) / V        subject to  V >= V_S,  r_T(V) <= 1       ->  R_max = 3600 * E_bat / (P_bat/V)*
P_bat(V), r_T(V) := battery-power, thrust-demand-ratio of motor-propeller-part-load at V
V_S              := stall-speed (quantity of application `clean`, read as an input)
```

**Produces** [[max-endurance]] · [[max-range]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[battery-capacity]] · [[dynamic-viscosity]] · [[speed-of-sound]] · [[components]] · [[motor-voltage-constant]] · [[motor-no-load-current]] · [[motor-circuit-resistance]] · [[battery-voltage]] · [[motor-max-power]] · [[propeller-diameter]] · [[motor-efficiency]] · [[stall-speed]]

**Kind: an optimisation problem.** The speed is not given but found: the one at which the **battery power** of the part-load chain is least (endurance) or the battery energy per metre `P_bat/V` is least (range). The domain is the speeds the airplane can fly level — from the stall speed up to where the required thrust reaches the full-throttle thrust (`r_T ≤ 1`, [[thrust-demand-ratio]]). This is the **optimised** value of decision 2 (maintainer, 2026-10-25, #1235); [[endurance-and-range]] gives the estimate at `V_mp` and `V_md`, which does not exceed it where its speeds lie inside the domain. Approval asks, on top of source and scale: **no bound active at the optimum** (an optimum at `V_S` or at `r_T = 1` is reported, not accepted silently) and **what is returned when the solver fails** — never a value.

**Ist ≠ Soll (#1235).** Ist: `app/services/endurance_service.py` converts aerodynamic power to battery power with one constant, η ≈ 0.52 (η_prop 0.65 × η_motor 0.85 × η_ESC 0.94, all assumptions). Soll: the app **must follow** this entry and take the battery power from the part-load chain (#1238).

**Source.** 🟡 PARTIAL. As in [[endurance-and-range]]: the energy balance `t = E_bat/P_bat`, `R = V·t` has no textbook source [no source]; Sadraey's closures (§4.2.5.2 Eq. 4.17, §4.2.5.4 Eq. 4.22–4.23) are the constant-`η_P` special case, in which the optima fall at `V_md` and `V_mp`.

**Validity in the RC/UAV regime (ADR 0028).** The optimum moves with the propeller's efficiency curve, which at Re₀.₇₅ ≈ 15–100 k depends strongly on advance ratio and Reynolds number (Brandt & Selig 2011 §IV; Deters, Ananda & Selig 2014 §V.A–B), and the lowest speeds of the domain sit at high `C_L`, where the low-Re polar is least certain (Sharpe 2024 §7.2.4). Battery sag, the usable fraction of the charge and reserve are not modelled [no source]; the battery is taken as its full rated energy. Mach is no concern (Anderson §1.10.3).

*Remark (gh-1415, undated):* the stall speed is read as the input `v_s` ← [[stall-speed]] (application `clean`) instead of being embedded as `stall-speed.clean`. The embed mechanism as built hands out plain relations only; the stall speed is an AeroBuildup solve (a coroutine, not a relation), and reading its quantity is the same value, from the same producer (ADR 0022), as embedding it. The entry's own wording "embeds the stall speed for its domain" is therefore met by an input edge.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| `aero_kernel/formulas/endurance_and_range_optimum.py` | DEVIATES | 🟢 | The part-load relation of [[motor-propeller-part-load]] is evaluated at the speeds of a **scan** that starts at the stall speed `V_S` and rises by the ratio `endurance_speed_ratio` (`config.yaml`, 1.1) until the drive train cannot hold the speed (`r_T > 1`) or the part-load chain fails there (`outside_propeller_table`: the table holds no balance, e.g. a drag beyond its thrust); the best scan speed of each objective (`P_bat`, `P_bat / V`) is refined by golden section inside its two neighbouring cells to the relative width `endurance_speed_tolerance` (1 %). Speeds at which the level-flight solve does not converge near `V_S` (the weight is carried only at the lift peak) are not part of the domain: the domain starts at the lowest scan speed that solves. **The domain is the first contiguous run of holdable speeds**: the scan ends at the first speed after the domain began at which the drive train cannot hold the speed (`r_T > 1`, bound `full_throttle`), the table holds no balance (`propeller_table`), or its full-throttle thrust has vanished (`no_thrust_at_full_throttle` or `propeller_windmilling`, bound `full_throttle_thrust`); a hole inside the range ends the domain there and is reported as the bound, no further mechanism. The scan also ends at the **Mach limit** of the RC/UAV regime, `mach_limit` = 0.3 of the canon rule `reynolds-mach-regime` (ADR 0028: incompressible flow) times the speed of sound `a`; an optimum there is reported as the bound `mach_limit`. If `V_S` itself does not solve, the bound is named `level_flight_solution`, not `stall_speed`. The optimum is **declared, never silent**: where the best speed is a domain edge (the lowest solvable speed, or the last speed the drive train holds) the `warning` `optimum_at_domain_bound` names the bound, and `detail` lists the edge speeds; the upper edge is resolved to the scan cell, not to the exact `r_T = 1` crossing. If no scan speed solves, the result is the declared failure `no_level_flight_speed`. One scan and two refinements share every evaluated speed (a speed is evaluated once). Unimodality of `P_bat(V)` is assumed between neighbouring scan speeds; a second minimum narrower than a cell is not found. **Route B only** (complete data, as decided for the powertrain, gh-1411): an absent `r_m` or `i_0` ends as `missing_input`, and `p_mot_max` and `eta_mot` are bound and not read; route A (assumed efficiency) is not built. The energy is the rated pack energy `E_bat` (nominal cell voltage, no usable fraction, no sag, no reserve), as the entry declares; no factor is applied. `outside_propeller_table` of the part-load search at a speed ends the evaluation of that speed. Warnings forwarded: those of the two optimum speeds only (their level-flight caveats, the route `notice` extended with the rated-energy statement) and the bound warning, which names the bound, its speed and the best speed and states no judgement. Cost: roughly 20 to 45 part-load evaluations (a scan of about ten speeds plus two golden-section refinements); the whole request took 3.9 to 4.1 s on the Avistar Elite (measured gh-1415); cost class `seconds`. On the Avistar Elite at 3.70 kg after gh-1417: 4948 s and 72.5 km, no bound active (before it, a hole of the rpm search at 17.0 to 17.75 m/s put the range on a false bound `propeller_table` at 16.83 m/s; the value was the same 72.5 km) |

No register node is mapped to this entry.

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
