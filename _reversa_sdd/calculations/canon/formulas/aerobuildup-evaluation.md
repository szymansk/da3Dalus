---
canon: aerobuildup-evaluation
entry: formula
kind: procedure
shape: law
status: draft
output: lift-force, drag-force, lift-curve-slope, zero-lift-angle
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

# Aerodynamic evaluation of the airplane at an operating point

**Canonical form**

```
L, D, CLa, alpha_0 := AeroBuildup(airplane, OperatingPoint(V, alpha, atmosphere))
```

**Produces** [[lift-force]] · [[drag-force]] · [[lift-curve-slope]] · [[zero-lift-angle]]  ·  **from** [[airplane]] · [[flight-speed]] · [[angle-of-attack]] · [[air-density]]

**Kind: a procedure — the solver.** AeroBuildup returns lift and drag in newtons and, with
`run_with_stability_derivatives()`, the lift-curve slope (key `CLa`, per radian, by finite
difference). The zero-lift angle is read off the computed polar. The span efficiency is produced once, at the cruise point, by [[parasite-drag-split]] (ADR 0004).
The Reynolds number is formed inside, per section, from `V` and the local chord.

**Why this entry exists.** These were inputs, though they are the most airplane-dependent
quantities of all: they are what the solver says about this aircraft at this operating
point. Verified against the installed AeroSandbox 4.2.9 source.
