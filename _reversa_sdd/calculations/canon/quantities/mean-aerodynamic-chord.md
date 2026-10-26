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
figure: mean-aerodynamic-chord
---

# Mean aerodynamic chord · `c_MAC`

Chord used to form the Reynolds number for the speed-scheduled polar lookup.

What is measured: ASB 4.2.9, `geometry/wing.py`, `Wing.mean_aerodynamic_chord` (line 468; "the generalized methodology" of https://core.ac.uk/download/pdf/79175663.pdf). For each lofted section between two stations it takes the trapezoid's MAC length `(2/3)·c_inner·(1 + λ + λ²)/(1 + λ)` with `λ = c_outer/c_inner`, and then the mean of these lengths weighted by the sectional planform areas `area(_sectional=True)`. Those areas are measured along the panels in the y-z plane and do not include the centreline gap: ASB has no flag here, so the area and the span beside it carry the gap explicitly (see wing-reference-area) and this value does not.

The call: `main_wing.mean_aerodynamic_chord()`. For a flat wing, tapered or not, it equals Scholz's definition (Flugzeugentwurf, Wing Design §7.1): `c_MAC = (2/S)·∫₀^{b/2} c(y)² dy`. With dihedral the weighting is along the panels, so the value differs slightly from the projected integral.

**Unit.** `m`

**Produced by.** [[airplane-geometry]]

**Used by.** [[cg-for-target-margin]] · [[static-margin]]
