---
canon: wing-span
kind: quantity
symbol: b_ref
unit: m
role: derived
tags:
  - canon/quantity
  - stage/references
  - module/construction
  - group/geometry-references
  - role/derived
type: scalar
figure: wing-area-span
---

# Reference span · `b_ref`

Reference wing span of the built airplane.

What is measured: the y-z extent of the main wing, both halves, carried to the centreline: a root that does not lie on y = 0 counts from the centreline, so the span and the reference area describe the same planform. The reference wing runs through the fuselage (Scholz, Flugzeugentwurf, Wing Design §7.1).

The call: `main_wing.span(type="yz", include_centerline_distance=True)`, both arguments set in the kernel code and never left to ASB's defaults (ASB 4.2.9, `geometry/wing.py`, `Wing.span`, flag `include_centerline_distance`). Why not ASB's automatic values: `asb.Airplane`, when it derives its reference values itself, takes the area without the gap and the span with it, from the first wing in the list, and marks that derivation "# Note: will be deprecated" (`aerosandbox/geometry/airplane.py:57-61`, ASB 4.2.9); the kernel sets the values explicitly instead.

**Unit.** `m`

**Produced by.** [[airplane-geometry]]

**Used by.** [[aspect-ratio]] · [[roll-rate]] · [[mean-geometric-chord]] · [[spiral-parameter]] · [[vertical-tail-volume]]
