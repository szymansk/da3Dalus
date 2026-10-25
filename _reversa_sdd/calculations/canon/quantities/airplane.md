---
canon: airplane
kind: quantity
symbol: airplane
unit: —
role: input
status: draft
tags:
  - canon/quantity
  - module/construction
  - role/input
type: airplane
---

# Airplane · `airplane`

The aircraft geometry as handed to the solver — wings with their sections and airfoils,
fuselage, tail, reference values; **geometry only** (maintainer, 2026-10-17, S15). The fitted
motor, battery and propeller are the separate input [[components]]. Not a number but the model
every solver-backed relation is evaluated on. Listed as an input so that the graph says the truth for invalidation (A1):
a change to the geometry dirties every quantity the solver produces.

**Used by.** [[aerobuildup-evaluation]] · [[aileron-deflection-required]] · [[airplane-configuration]] · [[airplane-geometry]] · [[best-angle-of-climb]] · [[best-rate-of-climb]] · [[control-surface-hinge-moments]] · [[cruise-target-performance]] · [[dive-speed]] · [[endurance-and-range]] · [[lateral-static-stability-app]] · [[lateral-static-stability-md]] · [[maneuvering-speed]] · [[mass-envelope]] · [[max-level-speed]] · [[max-sustained-turn-rate]] · [[min-sustained-turn-radius]] · [[minimum-drag-speed-from-polar]] · [[minimum-sink-speed-from-polar]] · [[neutral-point]] · [[parabolic-polar-fit]] · [[roll-rate]] · [[roll-rate-cruise-target]] · [[spanwise-loads]] · [[spar-break-load-factor]] · [[spiral-parameter]] · [[stall-break]] · [[stall-speed]] · [[static-margin-probe]] · [[static-thrust-to-weight]] · [[vertical-tail-volume]]
