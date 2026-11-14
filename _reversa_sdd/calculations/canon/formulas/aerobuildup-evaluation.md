---
canon: aerobuildup-evaluation
entry: formula
kind: procedure
tool: AB
shape: law
status: approved
output: lift-force, drag-force
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
outputs: {l: lift-force, d: drag-force}
---

# Aerodynamic evaluation of the airplane at an operating point

**Canonical form**

```
r    := AeroBuildup(airplane, OperatingPoint(V, alpha, atmosphere(rho, mu, a)))
L    := r.L
D    := r.D_profile + k_e,D0 * r.D_induced        (k_e,D0: rule aerobuildup-induced-drag)
```

**Produces** [[lift-force]] · [[drag-force]]  ·  **from** [[airplane]] · [[flight-speed]] · [[angle-of-attack]] · [[air-density]] · [[dynamic-viscosity]] · [[speed-of-sound]]

**Kind: a procedure — the solver.** AeroBuildup returns lift and drag in newtons. `L` is AeroBuildup's. **`D` is the kernel's drag (maintainer decision 2026-11-03, #1346, path B).** AeroBuildup's induced drag uses the Nita & Scholz (2012) Oswald factor, the inviscid (geometric) factor `e_theo` times the full-scale viscous factor `k_e,D0 = 0.83625` (`inviscid.py:63, 67-74, 81`), which folds the lift-dependent part of the profile drag into `e` (Anderson 6e §6.7.2). AeroBuildup also integrates NeuralFoil's section `c_d(c_l)` at each local Reynolds number (`aero_buildup.py:817`), which already contains that drag, so AeroBuildup counts it twice. Where profile drag comes from a section polar, the inviscid factor is the right one (Anderson §5.3.3). The kernel therefore takes the factor out: `D = D_profile + k_e,D0 · D_induced`, with `D_profile` and `D_induced` as AeroBuildup returns them (`aero_buildup.py:344-345`). The induced drag is `L² / (q π b_eff²)` with `b_eff²` a scale-free softmax of the components' `b² e` (`aero_buildup.py:279-290`), which is homogeneous of degree 1, and every wing's `e` carries `k_e,D0`, so this equals AeroBuildup with `k_e,D0 = 1` while the wings dominate the softmax — measured on BRYAN, WIESEL, CHEKKER and BELEMNITOS: ratio 0.836250 for all four (#1346). The fuselage's own `e = 0.95` (`aero_buildup.py:1221`) carries no `k_e,D0`, so where the fuselage term counts the equality is not exact (rule `aerobuildup-induced-drag`); its share of the softmax is negligible on the fleet (that is what the ratio measures). AeroSandbox is not patched, and there is one producer of drag: the same function (`aero_kernel/solvers/aerobuildup.py:kernel_drag`) serves this single evaluation, the alpha sweep of [[stall-speed]] and the model function of the IPOPT problems ([[minimum-drag-speed]], [[minimum-sink-speed]]). `k_e,D0` is the parameter `k_e_d0` of the rule `aerobuildup-induced-drag` (`rules.yaml`, sourced, adopted; it appears in `provenance.rules_used`); the aero tier checks that it equals AeroSandbox's (`oswalds_efficiency / e_theo`, to 1·10⁻⁹). **Declared (ADR 0020):** every value that carries the correction gets the `notice` `induced_drag_viscous_factor_removed`, one per evaluation (this entry, [[minimum-drag-speed]], [[minimum-sink-speed]]; not [[stall-speed]], whose values read lift only, while the formula that reads its polar's `C_D` declares it), with `k_e,D0` and the share of AeroBuildup's induced drag removed (`1 − k_e,D0` = 16.4 %) in `detail`. **Measured effect (#1346):** AeroBuildup's induced drag against AVL Trefftz at `C_L` 0.9 was +24 … +28 %; without the factor +3.7 … +6.9 %; NeuralFoil's lift-dependent profile drag is 0.3–1.3 × the term the factor added. The remaining gap is left to flight calibration (BELEMNITOS, #1173 point 4). The Oswald factor shown to users comes from [[parabolic-polar-fit]].
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
margin). The substitution is declared per section (ADR 0020): the notice `fuselage_section_equivalent`
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
**Canopies and contours.** Before the conversion, every body of role `canopy` is merged, for the solvers
only, into the body it sits on (rule `canopy-merge`, #1355, maintainer 2026-11-05: only the visible part of
a canopy counts); the merged sections are declared by the notice `canopy_merged_into_fuselage`, and the
stored document is not changed. AeroBuildup and AVL receive the same merged bodies
(`aero_kernel/solver_bodies.py`, one producer). AeroBuildup alone then sees each merged body on a
straight axis: the z of every section centre is placed on the least-squares line z(x) through all that
body's centres, because AeroBuildup takes each segment's axis from two consecutive centres and would
give a stepped centre crossflow drag at α = 0 (rule `fuselage-axis-straightened`, #1358, maintainer
2026-11-07; declared by the notice `fuselage_axis_straightened`); AVL keeps the true centres. A
section's measured point contour (rule `fuselage-contour`, #1349) is never read by the solvers: they
keep the super-ellipse parameters.

**Why this entry exists.** These were inputs, though they are the most airplane-dependent
quantities of all: they are what the solver says about this aircraft at this operating
point. Verified against the installed AeroSandbox 4.2.9 source.

**Source.** 🟢 Sharpe, PhD thesis 2024: AeroBuildup §5.3, validation §5.4, NeuralFoil analysis confidence §7.2.4, training data §7.2.5. Nita & Scholz (2012), "Estimating the Oswald Factor from Basic Aircraft Geometrical Parameters", Section 5, as cited and implemented in AeroSandbox 4.2.9 `library/aerodynamics/inviscid.py` (the class values of `k_e,D0` read from that transcription; the paper itself is not in the vault, an open gap). Anderson, Fundamentals of Aerodynamics 6e, §6.7.2 (the Oswald factor of the airplane polar absorbs the lift-dependent parasite drag) and §5.3.3 (span efficiency from lifting-line theory). The removal: maintainer decision 2026-11-03, #1346 (path B; the rejected paths were A, keep and declare, and C, an AVL method world).

**Validity in the RC/UAV regime (ADR 0028).** NeuralFoil supplies the section data; its training data cover Re_c of 1.9·10³ to 2.6·10⁸ (95 %; Sharpe 2024 §7.2.5), so the whole regime is inside the trained range. AeroBuildup calls NeuralFoil with its defaults — free transition, `n_crit = 9`, `xtr = 1` (`airfoil.py:651-653`, not overridden in `aero_buildup.py:795-803`) — so the polar is a smooth-surface polar: a turbulator or a rough printed surface is not represented, which matters below Re 7·10⁴. NeuralFoil's own analysis confidence drops sharply near Re_c ≈ 8·10⁴ at C_L ≈ 1.0, where a laminar separation bubble forms (Sharpe 2024 §7.2.4). AeroBuildup was cross-validated on an RC sailplane at Re_c = 1.55·10⁵, M = 0.044 (§5.4): lift and drag polars agree with nonlinear lifting line. Main-wing downwash on the tail is omitted for lift (§5.3), so tail lift is over-counted. The internal `e` uses a viscous factor averaged over four full-scale classes (jet 0.873, business jet 0.864, turboprop 0.804, general aviation 0.804; `inviscid.py:67-74`), none of them RC or UAV (ADR 0028); the kernel removes it (see Kind), so the drag it returns carries the inviscid Nita & Scholz factor and NeuralFoil's viscous drag at the local Reynolds number. Mach ≤ 0.3: compressibility is negligible. **The regime check** (ADR 0028, amended 2026-11-01, #1342) evaluates the chord Reynolds number at every station and reports one warning per surface, judged at its mean aerodynamic chord (below 3·10⁴ a `warning`, 3·10⁴–7·10⁴ a `notice`, above 10⁶ a `notice`), and one `warning` per control device with a station of its span below 3·10⁴; each carries where and how much of the surface or device it concerns. Mach above 0.6 is an `error`.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| `aero_kernel/formulas/aerobuildup_evaluation.py` | EXACT | 🟢 | one numeric AeroBuildup run at `(V, α)` in the bound air state, by the OPT adapter (`OptiAdapter.evaluate`), which owns every AeroBuildup call (ADR 0022); `L` as AeroBuildup returns it, `D` the kernel's drag (`solvers/aerobuildup.py:kernel_drag`, `D_profile + k_e,D0 · D_induced`, #1346) with the notice `induced_drag_viscous_factor_removed`; a deflected flap is evaluated and declared, any other deflected device refused |

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

> **Reopened for approval (2026-10-31).** The lift-curve slope and the zero-lift angle are no longer outputs
> of this entry. They moved to [[zero-lift-angle]], where `α_0` is the root of `C_L(V, α)` and
> `C_Lα` is read at that root, at the speed of each optimum. Read off this entry's single point, they
> depended on the caller's α: BRYAN at 4°: `α_0` −7.2° against the root's −3.6° (maintainer, 2026-10-31:
> "Ist der Nullauftriebswinkel nicht das Ergebnis eines einfachen Opti-Laufs?"). The entry is back to
> `draft` because its outputs changed; the rest of the text is as approved on 2026-10-25.

> **Approved again** (maintainer, 2026-11-01) with the outputs `L` and `D` only. The reference of the declared
> caveat moved from ADR 0023 to ADR 0028, which supersedes it; nothing else changed. When #1317 binds the
> analysis geometry (`analysis-airplane`) instead of `airplane`, the changed input brings this entry back for a
> short confirmation.

> **Reopened for approval (2026-11-03, #1346).** The drag output changed: `D` is no longer AeroBuildup's total
> drag but `D_profile + k_e,D0 · D_induced` (maintainer decision 2026-11-03, path B: the full-scale viscous
> factor removed from AeroBuildup's induced drag, because NeuralFoil's section polars already carry the
> lift-dependent profile drag). `L`, the inputs and the rest of the procedure are unchanged. The entry is back
> to `draft` because its computation changed.

> **Approved again** (maintainer, 2026-11-07) with `D = D_profile + k_e,D0 · D_induced` (#1346). The paragraph
> "Canopies and contours" was added on approval (text only, no change to the computation): it names the
> canopy merge (#1355) and states that the solvers do not read the point contour (#1349).
