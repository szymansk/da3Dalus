---
canon: wing-reference-area
kind: quantity
symbol: S_ref
unit: m^2
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

# Wing reference area · `S_ref`

Reference area of the built AeroSandbox airplane, the denominator of every coefficient in the chain.

What is measured: the planform area of the main wing, measured along the panels (a loft of quadrilateral mean-camber surfaces between the sections, not a projection onto the x-y plane), with the centreline gap included. A root that does not lie on y = 0 is extruded to the centreline with the wing's geometric chord as the width. The reference wing runs through the fuselage (Scholz, Flugzeugentwurf, Wing Design §7.1: the reference wing area is carried to the centreline).

The call: `main_wing.area(type="planform", include_centerline_distance=True)`, both arguments set in the kernel code and never left to ASB's defaults. ASB 4.2.9, `geometry/wing.py`, `Wing.area`: "we first figure out which WingXSec is closest to the centerline plane … we imagine that this WingXSec is extruded along the Y axis to the centerline plane (assuming a straight extrusion to produce a rectangular mid-camber surface). In doing so, we use the wing geometric chord as the extrusion width." Why not ASB's automatic values: `asb.Airplane`, when it derives its reference values itself, takes the area without the gap and the span with it, from the first wing in the list, and marks that derivation "# Note: will be deprecated" (`aerosandbox/geometry/airplane.py:57-61`, ASB 4.2.9); the kernel sets the values explicitly instead.

**Unit.** `m^2`

**Produced by.** [[airplane-geometry]]

**Used by.** [[aspect-ratio]] · [[lift-coefficient-required]] · [[mean-geometric-chord]] · [[wing-loading]] · [[spiral-parameter]] · [[vertical-tail-volume]]
