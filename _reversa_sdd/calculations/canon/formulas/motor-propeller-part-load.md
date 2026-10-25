---
canon: motor-propeller-part-load
entry: formula
kind: procedure
tool: OPT
shape: route
status: draft
output: propeller-speed-part-load, battery-current, battery-power, thrust-demand-ratio
source_status: PARTIAL
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/partial
  - dim/procedural
  - shape/route
  - kind/procedure
  - status/draft
inputs:
  airplane: airplane
  m: aircraft-mass
  g: gravity
  rho: air-density
  components: components
  v: flight-speed
  k_v: motor-voltage-constant
  i_0: motor-no-load-current
  r_m: motor-circuit-resistance
  u_bat: battery-voltage
  p_mot_max: motor-max-power
  d_prop: propeller-diameter
  eta_mot: motor-efficiency
outputs:
  n_pl: propeller-speed-part-load
  i_bat: battery-current
  p_bat: battery-power
  r_t: thrust-demand-ratio
embeds: [motor-propeller-equilibrium, advance-ratio-from-speed, propeller-table-lookup, thrust-at-airspeed-from-coefficient]
variables: [flight-speed]
optional: [r_m, i_0]
postconditions:
  - {id: demand_within_full_throttle, parameter: r_t, on_violation: warning}
---

# Battery power and current in level flight, from the part-load drive train

**Canonical form**

```
solve for alpha at V:    L(V, alpha) = m * g                  D := D(V, alpha)
propeller at part load:  C_T(J) * rho * n_pl^2 * D_prop^4 = D,        J = V / (n_pl * D_prop)
shaft torque:            Q = C_P(J) * rho * n_pl^2 * D_prop^5 / (2*pi)
route B (R_m known):     I = I_0 + Q * K_v'                   (I_0 = 0 when absent)
                         U_m = I * R_m + 2*pi*n_pl / K_v'     P_bat = U_m * I
route A (R_m absent):    P_bat = 2*pi * n_pl * Q / eta_mot
both routes:             I_bat = P_bat / U_bat
demand against supply:   r_T = D / T_full(V)                  T_full from motor-propeller-equilibrium
```

**Produces** [[propeller-speed-part-load]] · [[battery-current]] · [[battery-power]] · [[thrust-demand-ratio]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[components]] · [[flight-speed]] · [[motor-voltage-constant]] · [[motor-no-load-current]] · [[motor-circuit-resistance]] · [[battery-voltage]] · [[motor-max-power]] · [[propeller-diameter]] · [[motor-efficiency]]

**Kind: a procedure with two routes, selected by data.** Flight time and range need the **battery power** at the speed flown, and in level flight the propeller does not run at full throttle: it turns where its thrust equals the drag. This entry solves that balance — the part-load counterpart of [[motor-propeller-equilibrium]], which answers only for full throttle (maintainer, 2026-10-25, #1235; "Weg 2"). It replaces the quotient 'aerodynamic power over one assumed total efficiency' (`propulsive-efficiency`, deleted, ADR 0021).

**Why a separate entry, not a second application of the equilibrium.** An application binds the same relation differently and every application binds every input. The part-load adds a condition (thrust = drag), an aerodynamic input (the drag at `V`) and four new outputs, and the nine entries that embed the equilibrium would all have to name an application and carry the new inputs. The two entries share the motor model, the propeller table and the routes; this one embeds the equilibrium for `T_full(V)`. Every output is a distinct quantity (ADR 0022).

**Route B — where the manufacturer publishes `R_m`.** The thrust balance fixes the propeller speed `n_pl` from the propeller table alone; the table's `C_P` gives the torque the motor must supply; Drela's model then gives the current, the terminal voltage (below the pack voltage by the throttle) and the electrical power. `R_m` is the **circuit** resistance (motor + ESC + cable; `Q-PT-6`), so the ESC's resistive loss is in `U_m·I`; its switching loss is not. `I_0` absent → `I_0 = 0` (BR-PT15), declared. The terminal power of an ideal chopper equals the battery power, so `I_bat = P_bat/U_bat`.

**Route A — otherwise.** Propeller shaft power from the APC table, divided by the motor efficiency [[motor-efficiency]]: the catalogue's `efficiency_pct` where the manufacturer publishes it, else the sourced default of [[motor-efficiency]], declared with a `practice` warning (ADR 0020, maintainer 2026-10-25). Route A is a **declared method limitation** and a `practice` warning names it (`Q-PT-6`). Nothing is measured; only published values are used (#1149). The efficiency is one number for the whole load range, and the ESC's loss is not in it — both declared. The default is the lower bound of the 75–85 % band (see [[motor-efficiency]]); at the lighter loads of cruise a motor usually runs closer to its peak, so route A tends to **over-state** the battery power there.

**Demand against supply — a value, not a verdict (A10).** `r_T = D/T_full(V)` is the drag over the thrust the same motor and propeller give at full throttle at this speed. `r_T > 1`: the speed cannot be held in level flight; the other three outputs then describe a demand the drive train cannot meet and are accompanied by a `practice` warning (postcondition `demand_within_full_throttle`). Whether that speed is of interest is the evaluation's business.

**Current against allowed current.** [[battery-current]] is a value next to [[battery-current-allowed]] (from [[airplane-components]]); the canon states both and compares nothing (A10). Burst ratings are not modelled.

**Source.** 🟡 PARTIAL. 🟢 for the motor model (Drela `motor1` §1.1, three-parameter DC model: `v = i·R + Ω/K_v`, `Q_m = (i − i_0)/K_Q`) and for `C_T`, `C_P` as the measured table quantities (Brandt & Selig 2011 §II.F). The assembly — thrust = drag fixes `n_pl`, then the motor model supplies the electrical side — is an elementary balance with no textbook source for the battery-electric case [no source]; Sadraey treats electric propulsion only descriptively (§8.3.1) and gives only the constant-`η_P` forms for propeller aircraft (§4.2.5.2, §4.2.5.4).

**Validity in the RC/UAV regime (ADR 0028).** Part load means a lower propeller speed than the full-throttle point, hence a lower blade Reynolds number: small propellers run at Re₀.₇₅ ≈ 15–100 k (Brandt & Selig 2011 §IV), where `C_T` and `C_P` change with Reynolds number (Deters, Ananda & Selig 2014 §V.A–B), and the table block is chosen by nearest rpm — at cruise rpm the blocks are the sparsest and the coefficients the least certain. `R_m` rises with winding temperature, so a cold value understates the loss (Drela §1.1.1, §2.1); `I_0` depends on shaft speed and is meaningful only near the rpm it was measured at (Drela §1.1); the model breaks down at very high current. The drag is the solver's (ADR 0026), transition-sensitive at model Reynolds numbers (Anderson §4.12). Battery voltage sag under load, the usable fraction of the charge and reserve are not modelled [no source]; Mach is no concern (Anderson §1.10.3).

## Implementations (0)

None in aero_kernel yet; no register node is mapped to this entry (kernel implementation of the part-load chain: follow-up of #1235).

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
