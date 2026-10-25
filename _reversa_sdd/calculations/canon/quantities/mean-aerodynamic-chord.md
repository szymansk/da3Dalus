---
canon: mean-aerodynamic-chord
kind: quantity
symbol: c_MAC
unit: m
role: derived
tags:
  - canon/quantity
  - stage/references
  - module/construction
  - group/geometry-references
  - role/derived
type: scalar
---

# Mean aerodynamic chord · `c_MAC`

Chord used to form the Reynolds number for the speed-scheduled polar lookup.

What is measured: the mean aerodynamic chord of the main wing as AeroSandbox defines it, the area-weighted integral of the chord over the panels (Scholz, Flugzeugentwurf, Wing Design §7.1: `c_MAC = (2/S)·∫ c(y)² dy`). The call is `main_wing.mean_aerodynamic_chord()`; ASB gives it no centreline flag, so it is the same on either setting. The area and span beside it carry the centreline gap explicitly (see wing-reference-area).

**Unit.** `m`

**Produced by.** [[airplane-geometry]]

**Used by.** [[cg-for-target-margin]] · [[static-margin]]
