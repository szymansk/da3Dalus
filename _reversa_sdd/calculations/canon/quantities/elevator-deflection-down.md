---
canon: elevator-deflection-down
kind: quantity
symbol: delta_e,down
unit: deg
role: input
status: draft
tags:
  - canon/quantity
  - module/control-deflections
  - role/input
type: scalar
---

# Elevator deflection, down · `delta_e,down`

The elevator angle the aft CG edge is trimmed with (at `V_max`). Also the elevator-down deflection a hinge moment is evaluated at ([[control-surface-hinge-moments]], application `elevator_down`). Sign as `deflection_deg` of the trailing-edge device in the geometry format. A design input, no default; the stops in the geometry are never referenced (maintainer,
2026-10-14).

**Unit.** `deg`

**Used by.** [[control-surface-hinge-moments]] · [[mass-envelope]]
