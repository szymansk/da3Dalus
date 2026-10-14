---
canon: flap-deflection-takeoff
kind: quantity
symbol: delta_f,TO
unit: deg
role: input
status: draft
tags:
  - canon/quantity
  - role/input
type: scalar
---

# Flap deflection in take-off configuration · `delta_f,TO`

The flap angle that defines the take-off configuration of the airplane ([[airplane-configuration]]). A
**design input**, with no default (maintainer, 2026-10-14). It is **not bounded by the stop**
`positive_deflection_deg` in the geometry: that stop may only be a first draft, and the canon is used to
find out which stop the wanted speed needs — the stop matters to the designer, not to the canon.

For orientation only, not a default: typical RC values are take-off 10–20°; Lennon gives 20°.

**Unit.** `deg`

**Used by.** [[airplane-configuration]]
