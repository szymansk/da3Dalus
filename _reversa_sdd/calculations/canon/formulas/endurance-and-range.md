---
canon: endurance-and-range
entry: formula
kind: procedure
tool: OPT
shape: law
status: draft
output: endurance-estimate, range-estimate
source_status: PARTIAL
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/partial
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
tex: t_{est} = \frac{3600\,E_{bat}}{P_{bat}(V_{mp})}, \qquad R_{est} = \frac{3600\,E_{bat}\,V_{md}}{P_{bat}(V_{md})}
inputs:
  airplane: airplane
  m: aircraft-mass
  g: gravity
  rho: air-density
  mu: dynamic-viscosity
  a: speed-of-sound
  e_bat: battery-capacity
  v_mp: minimum-sink-speed
  v_md: minimum-drag-speed
  components: components
  k_v: motor-voltage-constant
  i_0: motor-no-load-current
  r_m: motor-circuit-resistance
  u_bat: battery-voltage
  p_mot_max: motor-max-power
  d_prop: propeller-diameter
  eta_mot: motor-efficiency
outputs: {t_est: endurance-estimate, r_est: range-estimate}
embeds: [motor-propeller-part-load]
variables: [flight-speed]
optional: [r_m, i_0]
---

# Endurance and range at the airplane's own two speeds — the estimate

**Canonical form**

```
t_est = 3600 * E_bat / P_bat(V_mp)            R_est = V_md * t(V_md) = 3600 * E_bat * V_md / P_bat(V_md)
P_bat(V) := battery-power of motor-propeller-part-load at V   (thrust = drag, level flight)
```

**Produces** [[endurance-estimate]] · [[range-estimate]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[dynamic-viscosity]] · [[speed-of-sound]] · [[battery-capacity]] · [[minimum-sink-speed]] · [[minimum-drag-speed]] · [[components]] · [[motor-voltage-constant]] · [[motor-no-load-current]] · [[motor-circuit-resistance]] · [[battery-voltage]] · [[motor-max-power]] · [[propeller-diameter]] · [[motor-efficiency]]

**Kind: a procedure — the part-load chain at two named speeds.** The battery power comes from [[motor-propeller-part-load]] (thrust = drag, motor model, propeller table) at `V_mp`, the speed of least *aerodynamic* power, and at `V_md`, the speed of least drag; endurance is the rated energy over that power, `t = 3600·E_bat/P_bat`, and the range `R = V·t`. There is **no assumed drive-train efficiency** (maintainer, 2026-10-25, #1235).

**Two values, two quantities, not two authorities** (decision 2). This entry is the **estimate**, evaluated at the speeds the airplane itself defines. [[endurance-and-range-optimum]] gives the **optimised** value, where the battery power (endurance) or the battery energy per metre (range) is least. With the drive train in the balance, the propeller's efficiency changes with the speed, so the true optima can shift away from `V_mp` and `V_md`; where the estimate speeds lie inside the optimiser's domain (from the stall speed up to `r_T = 1`) the estimate is a feasible point of that problem and therefore never exceeds the optimum; outside it the estimate describes a speed the airplane cannot hold (ADR 0022: distinct names, `endurance-estimate` / `range-estimate` against `max-endurance` / `max-range`).

**One entry with two outputs, not two applications; the optimum a second entry.** The estimate needs the two speeds `V_mp` and `V_md` as inputs, the optimum needs none and instead the stall speed — different inputs (the optimum embeds the stall speed for its domain), and every application binds every input. Within this entry the two results share the inputs and the closure, so one entry with two outputs is the canon's usual shape (it was already so before the split).

**Ist ≠ Soll (#1235).** Ist: `app/services/endurance_service.py` converts aerodynamic power to battery power with one constant, η ≈ 0.52 (η_prop 0.65 × η_motor 0.85 × η_ESC 0.94, all assumptions). Soll: the app **must follow** this entry and take the battery power from the part-load chain (#1238).

**Replaces** (2026-10-02, maintainer) `cruise-speed-resolution`, `power-required-electrical`, `endurance-from-battery` and `range-from-endurance`; (2026-10-25, #1235) the quotient `D·V/η` with `propulsive-efficiency`. Both results are **properties of the aircraft**, no target involved.

**Source.** 🟡 PARTIAL. The speeds are Sadraey's closures for propeller aircraft: range is maximised at `(L/D)_max`, i.e. minimum drag (§4.2.5.2, Eq. 4.17), and endurance at maximum `C_L^{3/2}/C_D`, i.e. minimum power (§4.2.5.4, Eq. 4.22–4.23), both derived for fuel burn with constant `η_P` and SFC. The battery-electric balance `t = E_bat/P_bat`, `R = V·t` is an elementary energy balance with no textbook source [no source]; Sadraey treats electric propulsion only descriptively (§8.3.1). The battery power is that of [[motor-propeller-part-load]].

**Validity in the RC/UAV regime (ADR 0028).** The energy balance is regime-independent; the numbers carry the regime, and endurance is the more exposed: `V_mp` lies at high `C_L`, about `1.2–1.4·V_S` (Sadraey §4.2.5.4, Eq. 4.25), where the low-Re polar is least certain — NeuralFoil reports low confidence near `C_L ≈ 1` at `Re_c ≈ 8·10⁴` (Sharpe 2024 §7.2.4), and profile drag is transition-sensitive (Anderson §4.12). The drive-train side is as valid as [[motor-propeller-part-load]] (Re₀.₇₅ ≈ 15–100 k, Brandt & Selig 2011 §IV). Battery sag, the usable fraction of the charge and reserve are not modelled [no source]; the battery is taken as its full rated energy. Mach is no concern (Anderson §1.10.3).

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| `aero_kernel/formulas/endurance_and_range.py` | DEVIATES | 🟢 | `P_bat(V_mp)` and `P_bat(V_md)` from the embedded relation of [[motor-propeller-part-load]] (the level-flight point at the speed from the kernel's one lift-equals-weight solve, then the drive-train balance; the embedder passes every input), `t_est = 3600 E_bat / P_bat(V_mp)`, `R_est = 3600 E_bat V_md / P_bat(V_md)`. **Route B only** (complete data, as decided for the powertrain, gh-1411): an absent `r_m` or `i_0` ends as `missing_input`, and `p_mot_max` and `eta_mot` are bound and not read; route A (assumed efficiency) is not built. The energy is the rated pack energy `E_bat` (nominal cell voltage, no usable fraction, no sag, no reserve), as the entry declares; no factor is applied. `outside_propeller_table` of the part-load search at a speed ends the evaluation of that speed (`V_mp` or `V_md` beyond the table or beyond what the wing carries is the declared failure of the part-load chain, never a value). Warnings forwarded: the caveats of the two level-flight solves (regime, flap, kernel drag), the route `notice` of the drive train, and — for a speed at which the drive train cannot hold level flight (`r_T > 1`) — the `warning` `postcondition_violated` for the part-load postcondition `demand_within_full_throttle` (the value is still returned: a demand the drive train cannot meet, A10). Cost: two part-load evaluations, about 2 s (measured on the Avistar Elite, gh-1415) |

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
