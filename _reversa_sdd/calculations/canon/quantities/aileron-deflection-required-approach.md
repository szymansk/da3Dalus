---
canon: aileron-deflection-required-approach
kind: quantity
symbol: delta_a,req,app
unit: deg
role: output
uncertainty: interval
status: draft
tags:
  - canon/quantity
  - point/approach
  - role/output
type: scalar
---

# Aileron deflection needed at approach · `delta_a,req,app`

The symmetric aileron angle ±δ_a the approach roll-rate target needs. If the target lies above the
maximum roll rate a method reaches, there is no value in that world but the error
`target_above_method_maximum` — never a clipped angle.

**Unit.** `deg`

**Produced by.** [[aileron-deflection-required]]

**Uncertainty (A11).** Interval over the method worlds AeroBuildup and AVL (roll rate: 23 % spread on BRYAN in the prototype).
