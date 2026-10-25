---
canon: motor-efficiency
kind: quantity
symbol: eta_mot
unit: 1
role: input
status: draft
tags:
  - canon/quantity
  - module/construction
  - role/input
type: scalar
positive: true
---

# Motor efficiency · `eta_mot`

Efficiency of the fitted motor in route A of [[motor-propeller-equilibrium]] (the propeller absorbs at
most `eta_mot · P_mot,max`; maintainer, 2026-10-15, E1) and of [[motor-propeller-part-load]] (battery power = propeller shaft power over `eta_mot`). An input with a sourced default. Where the catalogue publishes the motor's efficiency (`efficiency_pct`) the caller passes that value; otherwise the sourced default is taken and the route that uses it declares it with a `practice` warning (ADR 0020, maintainer 2026-10-25, #1235). Whether the catalogue's `P_mot,max` is electrical
or shaft power is open — the source does not say.

**Unit.** `1`

**Used by.** [[best-angle-of-climb]] · [[best-rate-of-climb]] · [[cruise-target-performance]] · [[dive-speed]] · [[endurance-and-range]] · [[endurance-and-range-optimum]] · [[mass-envelope]] · [[max-level-speed]] · [[max-sustained-turn-rate]] · [[min-sustained-turn-radius]] · [[motor-propeller-equilibrium]] · [[motor-propeller-part-load]] · [[static-thrust-to-weight]]
