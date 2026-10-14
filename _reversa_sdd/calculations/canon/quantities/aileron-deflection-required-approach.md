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
  - role/output
type: scalar
---

# Aileron deflection needed at approach · `delta_a,req,app`

The symmetric aileron angle ±δ_a the approach roll-rate target needs. If no angle in the method's validity
range reaches it, there is no value but the error `no_solution_in_validity_range` — never a clipped angle.

**Unit.** `deg`

**Produced by.** [[aileron-deflection-required]]

**Unschärfe (A11).** Intervall über die Methodenwelten AeroBuildup und AVL (Rollrate: Streuung 23 % beim BRYAN).
