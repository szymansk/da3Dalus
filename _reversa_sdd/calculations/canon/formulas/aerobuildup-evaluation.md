---
canon: aerobuildup-evaluation
entry: formula
kind: procedure
tool: AB
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
difference). The zero-lift angle is read off the computed polar. Its internal induced-drag factor `e` is the empirical Nita & Scholz (2012) correlation times a full-scale viscous factor `k_e,D0 = 0.836` (`inviscid.py:25-46`); with NeuralFoil's section profile drag on top, lift-dependent profile drag is partly counted twice. **Declared caveat (ADR 0026, ADR 0023):** on BRYAN AeroBuildup `e = 0.805` against AVL's inviscid 0.875 — about 9 % more induced drag. The Oswald factor shown to users comes from [[parabolic-polar-fit]].
The Reynolds number is formed inside, per section, from `V` and the local chord.

**Why this entry exists.** These were inputs, though they are the most airplane-dependent
quantities of all: they are what the solver says about this aircraft at this operating
point. Verified against the installed AeroSandbox 4.2.9 source.
