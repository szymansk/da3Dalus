---
canon: airplane
kind: quantity
symbol: airplane
unit: —
role: input
status: draft
tags:
  - canon/quantity
  - role/input
---

# Airplane · `airplane`

The aircraft as handed to the solver — wings with their sections and airfoils, fuselage,
tail, reference values. Not a number but the model every solver-backed relation is
evaluated on. Listed as an input so that the graph says the truth for invalidation (A1):
a change to the geometry dirties every quantity the solver produces.

**Used by.** [[aerobuildup-evaluation]] · [[aileron-throw-fraction]] · [[airplane-components]] · [[airplane-geometry]] · [[best-angle-of-climb]] · [[best-rate-of-climb]] · [[butterfly-approach]] · [[cruise-target-performance]] · [[dive-speed]] · [[endurance-and-range]] · [[maneuvering-speed]] · [[max-level-speed]] · [[max-roll-rate-cruise-target]] · [[max-roll-rate]] · [[max-sustained-turn-rate]] · [[min-sustained-turn-radius]] · [[minimum-drag-speed-from-polar]] · [[minimum-sink-speed-from-polar]] · [[motor-propeller-equilibrium]] · [[neutral-point]] · [[parabolic-polar-fit]] · [[propeller-table-lookup]] · [[spar-break-load-factor]] · [[stall-speed]] · [[static-margin-probe]]
