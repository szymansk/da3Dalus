---
canon: centre-of-gravity-measured
kind: quantity
symbol: x_cg,meas
unit: m
role: input
status: draft
tags:
  - canon/quantity
  - module/mass-and-balance
  - role/input
type: scalar
---

# Centre of gravity, measured · `x_cg,meas`

Longitudinal CG position of an existing aircraft — measured or taken from the plan; a finding, not a design input (the design CG is [[centre-of-gravity-design]]). Position x in the geometry frame, aft positive, in m (maintainer, 2026-10-23, #1203; the app's CG field follows in #1209). **An input of the canon** like the mass (A6): entered, or summed from the components — not the canon's concern. Until #1254 lands this is stated in prose; it then becomes a `data:` kind evaluation.

**Unit.** `m`

**Used by.** [[static-margin]]
