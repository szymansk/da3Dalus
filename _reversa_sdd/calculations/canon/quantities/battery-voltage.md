---
canon: battery-voltage
kind: quantity
symbol: U_bat
unit: V
role: derived
tags:
  - canon/quantity
  - stage/references
  - module/construction
  - group/powertrain-motor-propeller
  - role/derived
type: scalar
---

# Battery voltage · `U_bat`

Pack voltage at the motor controller: cell count × [[cell-voltage-nominal]] (default 3.7 V, the LiPo value; the caller overrides it for another chemistry). Sag under load is not modelled; the value is the nominal one and is declared as such.

**Unit.** `V`

**Produced by.** [[airplane-components]]

**Used by.** [[best-angle-of-climb]] · [[best-rate-of-climb]] · [[cruise-target-performance]] · [[dive-speed]] · [[endurance-and-range]] · [[endurance-and-range-optimum]] · [[mass-envelope]] · [[max-level-speed]] · [[max-sustained-turn-rate]] · [[min-sustained-turn-radius]] · [[motor-propeller-equilibrium]] · [[motor-propeller-part-load]] · [[static-thrust-to-weight]]
