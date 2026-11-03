---
canon: drag-force
kind: quantity
symbol: D
unit: "N"
role: derived
tags:
  - canon/quantity
  - discipline/aerodynamics
  - stage/aero-model
  - group/aero-forces
  - role/derived
type: scalar
---

# Drag force · `D`

Dimensional drag of the airplane at the operating point: AeroBuildup's profile drag plus its induced drag
with the full-scale viscous factor taken out, `D_profile + k_e,D0 · D_induced` (the kernel's drag, #1346;
[[aerobuildup-evaluation]]).

**Unit.** `N`

**Produced by.** [[aerobuildup-evaluation]]

**Used by.** [[lift-to-drag-ratio]]
