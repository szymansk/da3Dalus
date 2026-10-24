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
inputs: {airplane: airplane, v: flight-speed, alpha: angle-of-attack, rho: air-density, mu: dynamic-viscosity, a: speed-of-sound}
outputs: {l: lift-force, d: drag-force, cl_alpha: lift-curve-slope, alpha_0: zero-lift-angle}
---

# Aerodynamic evaluation of the airplane at an operating point

**Canonical form**

```
L, D, CLa, alpha_0 := AeroBuildup(airplane, OperatingPoint(V, alpha, atmosphere(rho, mu, a)))
```

**Produces** [[lift-force]] · [[drag-force]] · [[lift-curve-slope]] · [[zero-lift-angle]]  ·  **from** [[airplane]] · [[flight-speed]] · [[angle-of-attack]] · [[air-density]] · [[dynamic-viscosity]] · [[speed-of-sound]]

**Kind: a procedure — the solver.** AeroBuildup returns lift and drag in newtons and, with
`run_with_stability_derivatives()`, the lift-curve slope (key `CLa`, per radian, by finite
difference). The zero-lift angle is read off the computed polar. Its internal induced-drag factor `e` is the empirical Nita & Scholz (2012) correlation times a full-scale viscous factor `k_e,D0 = 0.836` (`inviscid.py:25-46`); with NeuralFoil's section profile drag on top, lift-dependent profile drag is partly counted twice. **Declared caveat (ADR 0026, ADR 0023):** on BRYAN AeroBuildup `e = 0.805` against AVL's inviscid 0.875 — about 9 % more induced drag. The Oswald factor shown to users comes from [[parabolic-polar-fit]].
The Reynolds number is formed inside, per section, from `V` and the local chord, `Re = ρ·V·c/μ`, and the
Mach number as `V/a`, both from the bound atmosphere (#1201): the solver gets `ρ`, `μ` and `a` from
[[air-density-isa]] and builds no atmosphere of its own from an altitude.

**Why this entry exists.** These were inputs, though they are the most airplane-dependent
quantities of all: they are what the solver says about this aircraft at this operating
point. Verified against the installed AeroSandbox 4.2.9 source.

## Implementations (0)

None in aero_kernel yet; no register node is mapped to this entry.

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [ ] **Relation and method** — which equation it solves, and by which named method
- [ ] **Assumptions** — the conditions the method requires (bracketing, continuity, range)
- [ ] **Convergence** — the criterion, and what is returned and declared on failure
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.
