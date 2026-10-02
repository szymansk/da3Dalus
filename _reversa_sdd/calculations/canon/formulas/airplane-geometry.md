---
canon: airplane-geometry
entry: formula
kind: procedure
shape: law
status: draft
output: wing-reference-area, wing-span, mean-aerodynamic-chord, propeller-diameter
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
---

# Geometric properties of the airplane

**Canonical form**

```
S_ref, b_ref, c_MAC, D_prop := geometry of the airplane model
```

**Produces** [[wing-reference-area]] · [[wing-span]] · [[mean-aerodynamic-chord]] · [[propeller-diameter]]  ·  **from** [[airplane]]

**Kind: a procedure — an evaluation of the model.** These are properties of the aircraft, read or
integrated from its geometry: reference area and span from the main wing, the mean
aerodynamic chord as `(2/S)·∫c(y)² dy`, the propeller diameter from the chosen propeller,
the flap factor from the flap type. AeroSandbox provides the wing values directly
(`Wing.area()`, `Wing.span()`, `Wing.mean_aerodynamic_chord()`).

**Why this entry exists.** These quantities used to stand as free inputs. They are not: a
change to the wing changes all of them, and the graph has to say so, or invalidation (A1)
would leave every number computed from them standing after a geometry edit.
