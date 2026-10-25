---
canon: motor-no-load-current
kind: quantity
symbol: I_0
unit: A
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

# Motor no-load current · `I_0`

No-load current of the fitted motor, from the parts catalogue. Missing for 18 of 41 motors (#1149), so **optional**: absent, the torque balance runs with `I_0 = 0`, as BR-PT15 does today — declared with a `practice` warning, not silent.

**Unit.** `A`

**Produced by.** [[airplane-components]]

**Used by.** [[best-angle-of-climb]] · [[best-rate-of-climb]] · [[cruise-target-performance]] · [[dive-speed]] · [[endurance-and-range]] · [[endurance-and-range-optimum]] · [[mass-envelope]] · [[max-level-speed]] · [[max-sustained-turn-rate]] · [[min-sustained-turn-radius]] · [[motor-propeller-equilibrium]] · [[motor-propeller-part-load]] · [[static-thrust-to-weight]]
