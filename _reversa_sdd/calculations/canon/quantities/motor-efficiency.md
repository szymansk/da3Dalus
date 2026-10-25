---
canon: motor-efficiency
kind: quantity
symbol: eta_mot
unit: 1
role: derived
tags:
  - canon/quantity
  - stage/references
  - module/construction
  - group/powertrain-motor-propeller
  - role/derived
type: scalar
data:
  - component:brushless_motor.efficiency_pct
  - default:motor-efficiency
---

# Motor efficiency · `eta_mot`

Efficiency of the fitted motor in route A of [[motor-propeller-equilibrium]] (the propeller absorbs at
most `eta_mot · P_mot,max`; maintainer, 2026-10-15, E1) and of [[motor-propeller-part-load]] (battery power = propeller shaft power over `eta_mot`). A property of the motor, read by [[airplane-components]] from the catalogue field `brushless_motor.efficiency_pct` (percent, divided by 100; maintainer, 2026-10-25, #1290) where the manufacturer publishes it. For a motor without it (today 40 of 42 catalogue motors) the starting value of `defaults.yaml`, 0.75, is the fallback, declared with a `practice` warning (ADR 0020); the designer replaces it once a motor with a published efficiency is chosen. Whether the catalogue's `P_mot,max` is electrical
or shaft power is open — the source does not say.

**Unit.** `1`

**Produced by.** [[airplane-components]]

**Used by.** [[best-angle-of-climb]] · [[best-rate-of-climb]] · [[cruise-target-performance]] · [[dive-speed]] · [[endurance-and-range]] · [[endurance-and-range-optimum]] · [[mass-envelope]] · [[max-level-speed]] · [[max-sustained-turn-rate]] · [[min-sustained-turn-radius]] · [[motor-propeller-equilibrium]] · [[motor-propeller-part-load]] · [[static-thrust-to-weight]]
