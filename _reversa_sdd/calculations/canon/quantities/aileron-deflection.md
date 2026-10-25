---
canon: aileron-deflection
kind: quantity
symbol: delta_a
unit: deg
role: input
tags:
  - canon/quantity
  - module/control-deflections
  - role/input
type: scalar
data: app:OperatingPointSchema.control_deflections
---

# Aileron deflection · `delta_a`

One symmetric aileron angle: left and right at ±δ_a. A positive δ_a commands a roll to the right (right trailing edge up); the roll rate is then positive, a negative δ_a gives the mirrored result. A design input, no default; the stops in the
geometry are never referenced (maintainer, 2026-10-14). An up/down differential is not modelled (out of
the MVP, maintainer 2026-10-01).

**Unit.** `deg`

**Used by.** [[control-surface-hinge-moments]] · [[roll-rate]] · [[roll-rate-cruise-target]]
