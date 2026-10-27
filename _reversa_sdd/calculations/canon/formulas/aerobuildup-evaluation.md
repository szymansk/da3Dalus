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

**The airplane AeroBuildup receives: fuselage sections (#1307).** The kernel converts the geometry to one
`asb.Airplane` (`aero_kernel/solvers/asb_airplane.py`); a fuselage section is an `asb.FuselageXSec` of width
`2a`, height `2b` and one shape exponent `n` (`|y/a|^n + |z/b|^n = 1`, `n = 2` the ellipse, `n = 1` the diamond;
the same exponent as the geometry format's, proved against `xsec_area()` in the aero tier). The geometry format
lets the upper and the lower half carry their own exponent (`n`, `n_lower`), both sharing `a` and `b`; AeroSandbox
has one. Such a section is **not refused** but mapped to the **equivalent symmetric section** (maintainer,
2026-10-26): the same width `2a`, height `2b` and centre, and the one exponent `n_eq` that keeps the cross-section
**area**. With the quadrant area `a·b·f(n)`, `f(n) = Γ(1 + 1/n)² / Γ(1 + 2/n)`, the area of the two halves is
`2ab (f(n) + f(n_lower))` and that of the symmetric section `4ab f(n_eq)`, so `f(n_eq) = (f(n) + f(n_lower)) / 2`,
independent of `a` and `b`; `f` rises strictly with `n`, so `n_eq` lies between the two exponents and is found by
bisection to the relative area tolerance `opt_fuselage_area_tolerance` (`config.yaml`, 1·10⁻¹², a numerical
margin). The substitution is declared per section (ADR 0020): the `practice` warning `fuselage_section_equivalent`
(origin `airplane`; `detail`: the section path, `n`, `n_lower`, `n_equivalent`). What AeroBuildup reads of a
fuselage and what the section keeps: the **cross-section area** (slender-body lift and moment, base drag, the
volume) is kept exactly; the **width and height** (the effective span of the crossflow term) and the **centre**
are kept exactly; the **perimeter**, from which the wetted area and so the skin-friction drag follow, is kept only
approximately, because the perimeter of a super-ellipse is not linear in `f(n)`. Measured on the reference fleet
(exact numerical perimeter, true sections against equivalent ones): CHEKKER's 37 substituted sections (`n` between
10 and 47, the two exponents within 9 % of each other) differ by at most 0.004 % and the wetted area of the body by
0.001 %; WIESEL's 46 substituted sections (`n` above 1.7 and `n_lower` up to 8.5) by at most 2.06 % in the perimeter
(a section with `n` = 1.88 above and 7.6 below) and 0.59 % in the wetted area of the body. The perimeter and area
AeroSandbox then computes of the equivalent section are its own closed-form fits (`xsec_area` below 0.6 % from the
gamma function, `xsec_perimeter` within 0.3 % near `n` = 2 and up to 7 % at `n` ≈ 45, a property of ASB's fit at
the near-rectangular sections of CHEKKER, and independent of the substitution). The fuselage's STEP geometry is
the precise one; the sections are the simplified drag and layout model (the fuselage in the xsec roles).

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
