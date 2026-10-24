---
canon: linear-lift-curve-inverse
entry: formula
kind: law
tool: APP
shape: law
status: draft
output: angle-of-attack-best-glide-probe, angle-of-attack-minimum-sink-probe
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/law
  - status/draft
inputs: {cl: null, cl_alpha: lift-curve-slope, alpha_0: zero-lift-angle}
outputs: {alpha: null}
applications:
  - id: best_glide
    bind: {cl: lift-coefficient-best-glide}
    produce: {alpha: angle-of-attack-best-glide-probe}
  - id: minimum_sink
    bind: {cl: lift-coefficient-minimum-sink}
    produce: {alpha: angle-of-attack-minimum-sink-probe}
preconditions:
  - {id: cl_within_linear_range, parameter: cl, on_violation: error}
---

# Angle of attack from lift coefficient via the linear lift curve

**Canonical form**

```
alpha = alpha_0 + C_L / C_Lalpha   (converted to degrees)
```

**Produces** [[angle-of-attack-best-glide-probe]] · [[angle-of-attack-minimum-sink-probe]]  ·  **from** [[lift-coefficient-best-glide]] · [[lift-coefficient-minimum-sink]] · [[lift-curve-slope]] · [[zero-lift-angle]]

**A Probe since 2026-10-14 (maintainer, D2; A7).** The angles of attack at best glide and minimum sink
come from their optimisations ([[minimum-drag-speed-from-polar]], [[minimum-sink-speed-from-polar]]), where α
is a decision variable on the nonlinear polar at the right Reynolds number. This entry inverts the linear
lift curve at the `C_L` of each optimum and must agree with the optimum α; in the linear range a mismatch
measures the quality of the lift-curve fit. Its former stall application is deleted: it is wrong by
construction (see the 🔴 block below), and its α duplicated the stall optimum α of [[stall-speed]].

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity in the RC/UAV regime (ADR 0028)**.

ℹ️ **Reclassified** from `procedure` by the trial of 2026-08-18. It is the algebraic inverse of a linear relation, written as one expression: `alpha_rad = alpha_0_rad + cl / cl_alpha_per_rad` (app/services/assumption_compute_service.py:2021-2023). No iteration, no search, no bracketing — the parser failed on it, not the maths. Its COEFFICIENTS come from a fit (that fit is a separate node), but the relation itself is closed form.

> 🔴 **An assumption of this entry is broken in the code.** *(Ist ≠ Soll: the canon now states the
> limit as the precondition `cl_within_linear_range` below; this block records only that the app departs from it.)*
>
> app/services/analysis_service.py:488 and app/services/assumption_compute_service.py:664 evaluate the inverse at CL = CL_max to report alpha_stall. CL_max lies by definition in the nonlinear region, and outside the alpha in [-2°, +6°] window the coefficients were fitted and R^2-gated on (assumption_compute_service.py:1214-1219). The code applies no extrapolation guard and attaches no marker. Consequence: alpha_stall is a straight-line extrapolation of the pre-stall slope into the region where the real curve has already flattened, so the reported stall angle is systematically LOW (optimistic) — typically several degrees for a cambered RC section — and is presented to the user as a computed stall angle indistinguishable from an in-range value.

**Evaluated by.** None for the inverse itself (direct algebraic evaluation, assumption_compute_service.py:2003-2023). The coefficients CL_alpha and alpha_0 come from ordinary least squares (`np.linalg.lstsq` on the design matrix [alpha, 1], assumption_compute_service.py:1267-1271) over an AeroBuildup alpha-sweep sampled at 1° steps on alpha in [-2°, +6°] (9 points, assumption_compute_service.py:1239-1247), with alpha_0 = -CL_0/CL_alpha (line 1302).

**Accuracy.** Not applicable to the inverse — closed form, exact. The OLS fit does not converge either: it is a single exact solve of the normal equations. The criterion as configured is not a tolerance but an acceptance test: R^2 >= 0.995 on the 9-point grid (assumption_compute_service.py:1219, 1280-1289); below that the coefficients are discarded entirely.

**On failure.** _cl_to_alpha_deg returns None when CL_alpha or alpha_0 is absent, or CL_alpha <= 0 (assumption_compute_service.py:2017-2020). Upstream returns (None, None) on <3 finite points, on R^2 < 0.995, or on fitted CL_alpha <= 0 (lines 1257, 1281, 1293) — each with a `logger.warning` only. The alpha_stall_deg / alpha_min_sink_deg / alpha_best_glide_deg fields then serialise as None (analysis_service.py:507-509) and simply disappear from the UI. NOT declared as a DesignWarning: ADR 0020 is not satisfied — the user cannot tell 'no lift curve could be fitted' from 'not computed yet'.

**Dimensional check.** ⚪ procedural — not an algebraic law

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §4.3 (linear region, alpha_L=0, lift slope a_0) and §5.3.3 (finite-wing C_L = a*(alpha - alpha_L=0)). Scholz 08_HighLift §8.2 / Sadraey §5.4.3 list alpha_o and C_l_alpha as defining features of the lift curve. RC: Lennon Ch. 3 performs exactly this inversion in worked form (C_L = 0.211 divided by the 0.08/deg slope gives 2.64 deg, then subtract the E197 section's -2 deg zero-lift angle).

**The source writes it as**

```
Sources write the forward relation C_L = a*(alpha - alpha_0); the proposal inverts it. Anderson §5.3.3 adds a fact worth keeping: alpha_L=0 is unaffected by aspect ratio (at zero lift there is no downwash), so the section zero-lift angle may be used for the finite wing - the slope, not the intercept, is what AR changes.
```

**Validity in the RC/UAV regime (ADR 0028).** Valid ONLY inside the linear range, and that is a real restriction for two of the three quantities this formula is used for. Recovering alpha_stall by inverting the linear curve at C_L,max is wrong by construction, because the curve is non-linear precisely there - it will always understate the stall angle. The error is largest exactly at RC scale: Lennon records stall AoA dropping from 17 deg to 10 deg at low model Rn while the linear slope barely moves, so the linear extrapolation overshoots further the smaller the model. alpha at best glide and minimum sink are inside the linear range and are fine. The limit is stated
as the precondition `cl_within_linear_range` below.

## Preconditions on the bindings

**`cl_within_linear_range` — `C_L` must lie in the linear range of the lift curve (on `cl`; error).**
The inverse is valid only for a `C_L` whose angle `alpha_0 + C_L/C_Lalpha` falls inside the α window
the coefficients `C_Lalpha` and `alpha_0` were fitted on — the linear range of the lift curve, where
the fit is accepted. Outside it the result is a straight-line extrapolation of the pre-stall slope
into the region where the real curve has already flattened, and there is no value to report: the
violation is an **error**, not a warning. In particular the inverse **must not** be evaluated at
`C_L,max` to report a stall angle — `C_L,max` lies outside the linear range by definition; the stall
angle `alpha_S` comes from [[stall-speed]], where α is the decision variable of the stall optimum.
Both applications of this entry (`best_glide`, `minimum_sink`) bind a `C_L` that normally lies inside
the window; the check makes that explicit instead of assumed.

## Implementations (3)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[alpha-stall-deg]] | SPECIALISED | 🟢 | Evaluated at C_L = C_L,max to report the stall angle. Because the relation is linear, it e |
| [[alpha-best-glide-deg]] | SPECIALISED | 🟢 | Evaluated at the C_L of the best-glide point. |
| [[alpha-min-sink-deg]] | SPECIALISED | 🟢 | Evaluated at the C_L of the minimum-sink point. |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

