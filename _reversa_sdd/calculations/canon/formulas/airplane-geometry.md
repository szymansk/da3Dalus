---
canon: airplane-geometry
entry: formula
kind: procedure
tool: GEO
shape: law
status: draft
output: wing-reference-area, wing-span, mean-aerodynamic-chord
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
inputs: {airplane: airplane}
outputs:
  s_ref: wing-reference-area
  b_ref: wing-span
  c_mac: mean-aerodynamic-chord
---

# Geometric properties of the airplane

**Canonical form**

```
S_ref, b_ref, c_MAC := geometry of the airplane model
```

**Produces** [[wing-reference-area]] · [[wing-span]] · [[mean-aerodynamic-chord]]  ·  **from** [[airplane]]

**Kind: a procedure — an evaluation of the model.** These are properties of the aircraft, read or
integrated from its geometry: reference area and span from the main wing (the wing with surface_type main_wing, #1187), the mean
aerodynamic chord as `(2/S)·∫c(y)² dy`, the flap factor from the flap type.

**Definition (maintainer, 2026-10-22).** The reference values are the sections' chords and leading edges as
given, projected onto the x-y plane, panel by panel; twist does not change them. The kernel integrates the
sections itself. AeroSandbox's `Wing.area()`, `Wing.span()` and `Wing.mean_aerodynamic_chord()` are not used for
the reference values: their projection depends on twist (they measure along the quarter-chord line), and the
mean aerodynamic chord weights panels by their slant area. The app's current values are measured along the
panels and differ by up to about 2 % at 8° dihedral.

**Why this entry exists.** These quantities used to stand as free inputs. They are not: a
change to the wing changes all of them, and the graph has to say so, or invalidation (A1)
would leave every number computed from them standing after a geometry edit.
