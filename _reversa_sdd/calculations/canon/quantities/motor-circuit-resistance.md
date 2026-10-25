---
canon: motor-circuit-resistance
kind: quantity
symbol: R_m
unit: ohm
role: derived
tags:
  - canon/quantity
  - stage/references
  - module/construction
  - group/powertrain-motor-propeller
  - role/derived
type: scalar
data: component:brushless_motor.rm_ohm
---

# Motor resistance in the torque balance · `R_m`

Resistance in the torque balance, taken as the manufacturer's **winding resistance** (`component:brushless_motor.rm_ohm`).
The datasheet value is the winding only: ESC and cable resistance are not included, so the voltage loss is slightly
under-estimated (maintainer, 2026-10-25, #1251: "wie es im Modellbau üblich ist; das ist an allen Ecken keine genaue Wissenschaft,
es geht um eine grobe Aussage zum bestehenden Design."); route B declares this with a `practice` warning (ADR 0020). It is
the cold motor value, which runs optimistic, and must be labelled as such. `Q-PT-6` wording updated 2026-10-25 (formerly
"circuit, not winding: motor + ESC + cable"). Sourced only where a manufacturer publishes it, **never synthesised** from
`K_v` and `I_0` (`Q-PT-6`). Present for 0 of 41 catalogue motors today (#1149): the quantity maps to the field, but no motor
carries a value yet; where absent, [[motor-propeller-equilibrium]] takes route A (free-run rpm, power-limited, O11).

**Unit.** `ohm`

**Produced by.** [[airplane-components]]

**Used by.** [[best-angle-of-climb]] · [[best-rate-of-climb]] · [[cruise-target-performance]] · [[dive-speed]] · [[endurance-and-range]] · [[endurance-and-range-optimum]] · [[mass-envelope]] · [[max-level-speed]] · [[max-sustained-turn-rate]] · [[min-sustained-turn-radius]] · [[motor-propeller-equilibrium]] · [[motor-propeller-part-load]] · [[static-thrust-to-weight]]
