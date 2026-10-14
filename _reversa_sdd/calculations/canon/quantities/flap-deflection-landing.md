---
canon: flap-deflection-landing
kind: quantity
symbol: delta_f,LDG
unit: deg
role: input
status: draft
tags:
  - canon/quantity
  - role/input
type: scalar
---

# Flap deflection in landing configuration · `delta_f,LDG`

The flap angle that defines the landing configuration of the airplane ([[airplane-configuration]]). A
**design input**, with no default (maintainer, 2026-10-14). It is **not bounded by the stop**
`positive_deflection_deg` in the geometry: that stop may only be a first draft, and the canon is used to
find out which stop the wanted speed needs — the stop matters to the designer, not to the canon.

For orientation only, not a default: typical RC values are landing 30–45°; Lennon gives 40°.

**Unit.** `deg`

**Used by.** [[airplane-configuration]]
