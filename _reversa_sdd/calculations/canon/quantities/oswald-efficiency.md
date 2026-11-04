---
canon: oswald-efficiency
kind: quantity
symbol: e_osw
unit: 1
role: derived
tags:
  - canon/quantity
  - discipline/aerodynamics
  - stage/aero-model
  - group/aero-parabola
  - role/derived
type: scalar
---

# Oswald span efficiency factor · `e_osw`

Oswald factor of the parabola fitted to the solver polar (ADR 0026) — comparable with literature values. **Display only.** Not AeroBuildup's internal `e`, which is the empirical Nita & Scholz correlation with a full-scale viscous factor; the kernel takes that factor out of AeroBuildup's induced drag (#1346), so the polar this factor is fitted to carries the viscous lift-dependent drag once, from NeuralFoil.

**Unit.** `1`

**Produced by.** [[parabolic-polar-fit]]

**Used by.** [[induced-drag-factor]] · [[max-lift-to-drag-parabolic]]
