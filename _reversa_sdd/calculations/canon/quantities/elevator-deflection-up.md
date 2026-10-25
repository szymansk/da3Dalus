---
canon: elevator-deflection-up
kind: quantity
symbol: delta_e,up
unit: deg
role: input
tags:
  - canon/quantity
  - module/control-deflections
  - role/input
type: scalar
---

# Elevator deflection, up · `delta_e,up`

The elevator angle the front CG edge is trimmed with (stall, landing configuration). Also the elevator-up deflection a hinge moment is evaluated at ([[control-surface-hinge-moments]], application `elevator_up`). Sign as `deflection_deg` of the trailing-edge device in the geometry format. A design input, no default; the stops in the geometry are never referenced (maintainer,
2026-10-14).

**Unit.** `deg`

**Used by.** [[control-surface-hinge-moments]] · [[mass-envelope]]
