---
canon: components
kind: quantity
symbol: components
unit: —
role: input
status: draft
tags:
  - canon/quantity
  - module/construction
  - role/input
type: components
---

# Fitted components · `components`

The fitted-components document: motor, battery, and propeller with its APC table — what the aircraft is
built with, as distinct from its geometry ([[airplane]]). Not a number. An input with no default
(maintainer, 2026-10-17, S15): swapping a battery, motor or propeller dirties every quantity read from
it (A1), without touching the geometry.

**Used by.** [[airplane-components]] · [[best-angle-of-climb]] · [[best-rate-of-climb]] · [[dive-speed]] · [[mass-envelope]] · [[max-level-speed]] · [[max-sustained-turn-rate]] · [[min-sustained-turn-radius]] · [[motor-propeller-equilibrium]] · [[propeller-table-lookup]] · [[static-thrust-to-weight]]
