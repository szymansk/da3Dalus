---
canon: endurance-and-range
entry: formula
kind: procedure
tool: OPT
shape: law
status: draft
output: max-endurance, max-range
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
tex: t_{max} = \frac{3600\,E_{bat}\,\eta}{D(V_{mp})\,V_{mp}}, \qquad R_{max} = \frac{3600\,E_{bat}\,\eta}{D(V_{md})}
inputs:
  airplane: airplane
  m: aircraft-mass
  g: gravity
  rho: air-density
  e_bat: battery-capacity
  eta: propulsive-efficiency
  v_mp: minimum-sink-speed
  v_md: minimum-drag-speed
outputs: {t_max: max-endurance, r_max: max-range}
---

# Greatest endurance and greatest range — the two cruise closures

**Canonical form**

```
solve for alpha at V:   L(V, alpha) = m * g          D(V) := D(V, alpha)
t(V) = 3600 * E_bat * eta / ( D(V) * V )        R(V) = 3600 * E_bat * eta / D(V)
t_max = t(V_mp)        R_max = R(V_md)
```

**Produces** [[max-endurance]] · [[max-range]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[battery-capacity]] · [[propulsive-efficiency]] · [[minimum-sink-speed]] · [[minimum-drag-speed]]

**Kind: a procedure — the solver at a named speed.** At the speed the level-flight `α` is solved
from `L = m·g` (AeroBuildup), the drag `D` taken from the solver (ADR 0026). Power required is
`P = D·V/η`; endurance `t = 3600·E_bat/P`; range `R = V·t = 3600·η·E_bat/D` — so range is largest
where drag is smallest (`V_md`) and endurance where power is smallest (`V_mp`) (§3.5: two closures,
not three). Both factors of the range come from the **same** speed — the precondition §3.5 named.

**Declared simplifications.** `η` is one number for the whole drive train (`propulsive-efficiency`),
although the propeller's efficiency varies with the advance ratio; the battery is taken as its
usable energy, no voltage sag, no reserve.

**Replaces** (2026-10-02, maintainer) `cruise-speed-resolution` (`V_cruise := V_md`, a generic
quantity as output — A2 — and an undeclared substitution — ADR 0020), `power-required-electrical`,
`endurance-from-battery` and `range-from-endurance` (`R = V_cruise · t` with `t` at an unrelated
speed). Both results are **properties of the aircraft**, no target involved.

**Source.** 🟡 PARTIAL (the front matter still says SOURCED). The closures are Sadraey's, for propeller aircraft: range is maximised at `(L/D)_max`, i.e. minimum drag (§4.2.5.2, Eq. 4.17), and endurance at maximum `C_L^{3/2}/C_D`, i.e. minimum power (§4.2.5.4, Eq. 4.22–4.23), both derived for fuel burn with constant `η_P` and SFC. The battery-electric constant-mass form `t = E_bat·η/(D·V)`, `R = E_bat·η/D` is an elementary energy balance with no textbook source [no source]; Sadraey treats electric propulsion only descriptively (§8.3.1).

**Validity in the RC/UAV regime (ADR 0028).** The two closures are regime-independent: range is largest at the minimum-drag speed and endurance at the minimum-power speed. The numbers carry the regime, and endurance is the more exposed: `V_mp` lies at high `C_L`, about `1.2–1.4·V_S` (Sadraey §4.2.5.4, Eq. 4.25), where the low-Re polar is least certain — NeuralFoil reports low confidence near `C_L ≈ 1` at `Re_c ≈ 8·10⁴` (Sharpe 2024 §7.2.4), and profile drag is transition-sensitive (Anderson §4.12). The single `η` stands in for a small-propeller efficiency that spans 0.28–0.65 and degrades below a blade Re of about 10⁵ (Brandt & Selig 2011 §IV); since `η` varies with the advance ratio, the true optima may shift away from `V_md` / `V_mp` [no source]. Battery sag and reserve are not modelled [no source]; Mach is no concern (Anderson §1.10.3).

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
