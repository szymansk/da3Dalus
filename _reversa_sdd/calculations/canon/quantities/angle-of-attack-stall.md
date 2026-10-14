---
canon: angle-of-attack-stall
kind: quantity
symbol: alpha_stall
unit: deg
role: output
status: draft
tags:
  - canon/quantity
  - role/output
type: scalar
---

# Angle of attack at the stall · `alpha_stall`

Angle of attack at the stall: from `C_L,max,stall` (the second output of [[stall-speed]]) through the linear lift curve. Outside the curve's linear range by construction — see the 🔴 block in [[linear-lift-curve-inverse]]. Replaces `characteristic-angle-of-attack`, which carried three conditions in one quantity (A2; #1181).

**Unit.** `deg`

**Produced by.** [[linear-lift-curve-inverse]]
