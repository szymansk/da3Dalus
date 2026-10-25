---
canon: motor-circuit-resistance
kind: quantity
symbol: R_m
unit: ohm
role: derived
status: draft
tags:
  - canon/quantity
  - stage/references
  - module/construction
  - group/powertrain-motor-propeller
  - role/derived
type: scalar
---

# Circuit resistance of the drive · `R_m`

Resistance in the torque balance. **Circuit**, not winding: motor + ESC + cable (`Q-PT-6`) — a datasheet gives the cold motor value, which runs optimistic, and must be labelled as such. Sourced only where a manufacturer publishes it, **never synthesised** from `K_v` and `I_0` (`Q-PT-6`). Present for 0 of 41 catalogue motors today (#1149); where absent, [[motor-propeller-equilibrium]] takes route A (free-run rpm, power-limited, O11).

**Unit.** `ohm`

**Produced by.** [[airplane-components]]

**Used by.** [[best-angle-of-climb]] · [[best-rate-of-climb]] · [[cruise-target-performance]] · [[dive-speed]] · [[endurance-and-range]] · [[endurance-and-range-optimum]] · [[mass-envelope]] · [[max-level-speed]] · [[max-sustained-turn-rate]] · [[min-sustained-turn-radius]] · [[motor-propeller-equilibrium]] · [[motor-propeller-part-load]] · [[static-thrust-to-weight]]
