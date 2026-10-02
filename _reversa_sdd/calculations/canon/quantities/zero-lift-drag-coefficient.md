---
canon: zero-lift-drag-coefficient
kind: quantity
symbol: C_D0
unit: dimensionless
role: derived
status: draft
tags:
  - canon/quantity
  - role/derived
---

# Zero-lift (parasite) drag coefficient · `C_D0`

Zero-lift parasite drag coefficient of the parabola fitted to the solver polar over the operating C_L window (ADR 0026). **Display and the calculated value of the `cd0` design assumption (ADR 0010) — never an input to performance.** In the design direction an estimate (Scholz chain with `c_f` at the mission Reynolds number, O12).

**Unit.** `dimensionless`


> ⚠️ **2 formulas produce this one quantity.** That is the shape ADR 0022
> forbids unless one is derived from the others. Resolve during approval.

**Produced by.** [[parabolic-polar-fit]]

**Used by.** [[cruise-thrust-constraint]] · [[drag-polar]] · [[max-lift-to-drag-parabolic]] · [[minimum-drag-speed-closed-form]]
