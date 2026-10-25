---
canon: aerobuildup-evaluation
entry: formula
kind: procedure
tool: AB
shape: law
status: approved
output: lift-force, drag-force, lift-curve-slope, zero-lift-angle
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/approved
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

**Source.** 🟢 Sharpe, PhD thesis 2024: AeroBuildup §5.3, validation §5.4, NeuralFoil analysis confidence §7.2.4, training data §7.2.5. Nita & Scholz (2012), "Estimating the Oswald Factor from Basic Aircraft Geometrical Parameters", Section 5, as cited and implemented in AeroSandbox 4.2.9 `library/aerodynamics/inviscid.py`.

**Validity in the RC/UAV regime (ADR 0028).** NeuralFoil supplies the section data; its training data cover Re_c of 1.9·10³ to 2.6·10⁸ (95 %; Sharpe 2024 §7.2.5), so the whole regime is inside the trained range. AeroBuildup calls NeuralFoil with its defaults — free transition, `n_crit = 9`, `xtr = 1` (`airfoil.py:651-653`, not overridden in `aero_buildup.py:795-803`) — so the polar is a smooth-surface polar: a turbulator or a rough printed surface is not represented, which matters below Re 7·10⁴. NeuralFoil's own analysis confidence drops sharply near Re_c ≈ 8·10⁴ at C_L ≈ 1.0, where a laminar separation bubble forms (Sharpe 2024 §7.2.4). AeroBuildup was cross-validated on an RC sailplane at Re_c = 1.55·10⁵, M = 0.044 (§5.4): lift and drag polars agree with nonlinear lifting line. Main-wing downwash on the tail is omitted for lift (§5.3), so tail lift is over-counted. The internal `e` uses a viscous factor averaged over full-scale classes (`inviscid.py:66-73`) and is not checked at RC Reynolds numbers [no source for its RC error]. Mach ≤ 0.3: compressibility is negligible.

## Implementations (0)

None in aero_kernel yet; no register node is mapped to this entry.

## Approval

- [x] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [x] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [x] **Relation and method** — which equation it solves, and by which named method
- [x] **Assumptions** — the conditions the method requires (bracketing, continuity, range)
- [x] **Convergence** — the criterion, and what is returned and declared on failure
- [x] **Dimensions** — the check balances
- [x] **Implementations** — all agree, or each deviation is declared and justified
- [x] **Preconditions** — every binding condition holds, or the violation is ticketed
- [x] **Inputs approved** — no formula is approvable before its inputs are

> **Approved** (maintainer, 2026-10-25): AeroBuildup is the recognised method for these quantities, with the
> tool limits this entry declares. "Wir wollen ja nicht asb neu implementieren sondern nutzen wo es sinnvoll
> ist." Convergence and assumptions are AeroBuildup's own (a single evaluation, no iteration of ours). The
> implementation checklist item holds vacuously: there is no aero_kernel formula for this entry yet.
