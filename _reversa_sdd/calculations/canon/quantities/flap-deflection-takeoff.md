---
canon: flap-deflection-takeoff
kind: quantity
symbol: delta_f,TO
unit: deg
role: input
tags:
  - canon/quantity
  - module/control-deflections
  - role/input
type: scalar
data: app:OperatingPointSchema.control_deflections
---

# Flap deflection in take-off configuration · `delta_f,TO`

The flap angle that defines the take-off configuration of the airplane ([[airplane-configuration]]). A
**design input**, with no default (maintainer, 2026-10-14). It is **not bounded by the stop**
`positive_deflection_deg` in the geometry: that stop may only be a first draft, and the canon is used to
find out which stop the wanted speed needs — the stop matters to the designer, not to the canon.

Lennon: 20° take-off (slotted flap, 30 % chord) — orientation only, not a default.

**Unit.** `deg`

**Used by.** [[airplane-configuration]] · [[control-surface-hinge-moments]]
