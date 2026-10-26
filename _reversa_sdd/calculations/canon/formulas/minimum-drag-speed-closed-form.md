---
canon: minimum-drag-speed-closed-form
entry: formula
kind: law
tool: APP
shape: law
status: draft
output: minimum-drag-speed-probe
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - shape/law
  - kind/law
  - status/draft
inputs:
  w_s: wing-loading
  rho: air-density
  cd0: zero-lift-drag-coefficient
  k: induced-drag-factor
outputs: {v_md_probe: minimum-drag-speed-probe}
---

# Minimum-drag speed from the parabolic polar

**Canonical form**

```
V_md,probe = sqrt( 2*(W/S) / (rho * sqrt(C_D0 / k)) )
```

**Produces** [[minimum-drag-speed-probe]]  ·  **from** [[wing-loading]] · [[air-density]] · [[zero-lift-drag-coefficient]] · [[induced-drag-factor]]

**The Probe of [[minimum-drag-speed]] (maintainer decision 2026-10-25).** Its output [[minimum-drag-speed-probe]] `checks` [[minimum-drag-speed]], the value of the optimisation in [[minimum-drag-speed-from-polar]], which is the authority. The closed form assumes a constant zero-lift drag and a constant induced-drag factor; at our Reynolds numbers both depend on the speed. Comparing the two routes is a test (ADR 0022), not a second truth.

The formula itself is a law (Sadraey Eq. 4.80, an algebraic consequence of the parabolic polar); it is the quantity that is the probe, as for [[static-margin-probe]] and [[max-lift-to-drag-parabolic]].

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity in the RC/UAV regime (ADR 0028)**.

**Test that follows.** The probe and the optimisation reach the same quantity by different means under one assumption, a parabolic polar. A large deviation means the polar is not parabolic. That is a statement about the aircraft, not a defect of either route; it is reported and never averaged or substituted.

**Dimensional check.** 🟢 balances

**Source.** 🟢 SOURCED

> Sadraey, Aircraft Design: A Systems Engineering Approach, §4.3.5, Eq. 4.80: V_ROCmax = V_Dmin = sqrt( (2*W/(rho*S)) / sqrt(C_Do/K) ). Cited by Sadraey to his own Aircraft Performance reference [5].

**The source writes it as**

```
Identical to the proposal once W/S is factored (Sadraey writes 2W/(rho*S) grouped, the proposal writes 2*(W/S)/rho). Sadraey introduces it as the speed for maximum rate of climb of a JET; the same quantity is the minimum-drag speed for any aircraft.
```

**Validity in the RC/UAV regime (ADR 0028).** Valid at RC scale as an algebraic consequence of the parabolic polar, with the same caveat as max-lift-to-drag-parabolic: at Re 5e4-3e5 the polar is offset-parabolic, so C_D0 and k must be fitted over the C_L range of interest, not anchored at C_L = 0 (see zero-lift-drag-from-sweep). Do not let this closed form and the argmax-of-polar route both be authoritative - ADR 0022.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[v_md]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

**Own output since 2026-10-02.** As the Probe it must not produce `V_md` itself: it did, and
with `C_D0` and `e` now bound to the cruise point (ADR 0004) that closed a loop
`V_md → V_cruise → e → k → V_md`. Its value is `V_md,probe`, compared with the
optimisation's `V_md`; a mismatch beyond the parabola's known error at low Reynolds number
is reported, not substituted.
