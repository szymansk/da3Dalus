---
canon: motor-circuit-resistance
kind: quantity
symbol: R_m
unit: ohm
role: derived
status: draft
tags:
  - canon/quantity
  - role/derived
---

# Circuit resistance of the drive · `R_m`

Resistance in the torque balance. **Circuit**, not winding: motor + ESC + cable (`Q-PT-6`) — a datasheet gives the cold motor value, which runs optimistic, and must be labelled as such. Sourced only where a manufacturer publishes it, **never synthesised** from `K_v` and `I_0` (`Q-PT-6`). Present for 0 of 41 catalogue motors today (#1149); where absent, [[motor-propeller-equilibrium]] takes its fixed-RPM route.

**Unit.** `ohm`

**Produced by.** [[airplane-components]]

**Used by.** [[best-angle-of-climb]] · [[best-rate-of-climb]] · [[motor-propeller-equilibrium]]
