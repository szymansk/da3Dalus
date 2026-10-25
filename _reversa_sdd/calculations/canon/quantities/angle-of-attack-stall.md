---
canon: angle-of-attack-stall
kind: quantity
symbol: alpha_S
unit: deg
role: derived
tags:
  - canon/quantity
  - discipline/aerodynamics
  - stage/aero-model
  - group/aero-stall
  - role/derived
type: scalar
---

# Angle of attack at the stall · `alpha_stall`

Angle of attack at the stall (clean configuration, first `C_L` peak): the optimum α of [[stall-speed]], from the nonlinear polar at the right Reynolds
number (maintainer, 2026-10-14, D2). Replaces `characteristic-angle-of-attack`, which carried three
conditions in one quantity (A2; #1181).

**Unit.** `deg`

**Produced by.** [[stall-speed]]

**Used by.** [[stall-break]]
