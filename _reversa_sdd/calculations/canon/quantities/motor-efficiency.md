---
canon: motor-efficiency
kind: quantity
symbol: eta_mot
unit: 1
role: input
status: draft
tags:
  - canon/quantity
  - role/input
type: scalar
positive: true
---

# Motor efficiency · `eta_mot`

Efficiency of the fitted motor in route A of [[motor-propeller-equilibrium]]: the propeller absorbs at
most `eta_mot · P_mot,max` (maintainer, 2026-10-15, E1). An input with a sourced default; taking the
default is visible (INFO, `provenance.defaults_used`). Whether the catalogue's `P_mot,max` is electrical
or shaft power is open — the source does not say.

**Unit.** `1`

**Used by.** [[best-angle-of-climb]] · [[best-rate-of-climb]] · [[dive-speed]] · [[mass-envelope]] · [[max-level-speed]] · [[max-sustained-turn-rate]] · [[min-sustained-turn-radius]] · [[motor-propeller-equilibrium]] · [[static-thrust-to-weight]]
