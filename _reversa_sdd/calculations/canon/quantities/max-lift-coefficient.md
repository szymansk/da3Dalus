---
canon: max-lift-coefficient
kind: quantity
symbol: C_L,max,stall
unit: 1
role: derived
status: approved
tags:
  - canon/quantity
  - discipline/aerodynamics
  - stage/aero-model
  - role/derived
type: scalar
---

# Maximum lift coefficient (clean) · `C_L,max`

Maximum lift coefficient at the stall condition — the second output of the [[stall-speed]] optimisation (2026-10-01), evaluated at the stall's own Reynolds number. In the design direction, where no airplane exists yet, its source is open (O12).

**Unit.** `1`

**Produced by.** [[stall-speed]]

**Used by.** [[parabolic-polar-fit]] · [[stall-break]] · [[stall-wing-loading-limit]]
