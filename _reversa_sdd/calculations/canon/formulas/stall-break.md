---
canon: stall-break
entry: formula
kind: procedure
tool: OPT
shape: law
status: approved
output: alpha-break, stall-break-width
source_status: PARTIAL
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/partial
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/approved
inputs: {polar_s: polar-stall, alpha_s: angle-of-attack-stall, cl_max: max-lift-coefficient, f: stall-break-fraction, airplane: airplane}
outputs: {alpha_break: alpha-break, width: stall-break-width}
---

# Stall break from the post-peak branch of the computed polar

**Canonical form**

```
alpha_break = crossing of C_L(alpha) with (1 - f) * C_L,max on the branch past alpha_S
              (linear interpolation between the two bracketing samples)
width       = alpha_break - alpha_S
```

**Produces** [[alpha-break]] · [[stall-break-width]]  ·  **from** [[polar-stall]] · [[angle-of-attack-stall]] · [[max-lift-coefficient]] · [[stall-break-fraction]] · [[airplane]]

**Kind: a procedure.** There is no closed form, so an algorithm stands in its place. Source and scale are asked as of any entry — a procedure is not source-free: it either implements a published standard or solves a stated equation. **On top of that** it must say **under which assumptions it holds** and **when it converges**, including what it returns when it does not.

**Replaces** `stall-onset-detection` and `stall-onset-index` (#1219). The old entry returned an index into a sweep, taken from a first-difference test ("C_L fell and C_D rose against the previous sample") that no source publishes and that a single non-monotone solver sample could trigger; when the sweep did not bracket the event it returned the last or the peak sample as if it were a detection (an undeclared substitution, ADR 0020). This entry returns an angle with a stated definition and no value where it cannot bracket.

### Definition

`alpha_break` (α_break, deg) is the angle of attack **past the stall angle α_S at which the lift coefficient of the computed polar has fallen to the fraction (1 − f) of its peak** `C_L,max`: the lift curve has *broken*. `stall-break-width` (Δα_break = α_break − α_S, deg) is the distance from the peak to that break — how many degrees the lift takes to fall by the fraction f. The width is a number, not a class: this entry draws no line between an abrupt and a gentle stall (A10, the canon computes and does not judge).

`f` is [[stall-break-fraction]], a **defined value** (`basis: convention`, `defaults.yaml`): 0.10, adopted on the maintainer's word on 2026-10-24 (#1219). A second level would be a second named quantity, not a second input.

### The procedure

**Relation solved.** The crossing `C_L(alpha) = (1 - f) * C_L,max` on the falling branch past `alpha_S`, where `alpha_S` and `C_L,max` are the first peak of the same polar ([[stall-speed]] publishes all three together).

**Method.** Forward scan of the sampled polar from the sample at `alpha_S`; the first sample with `C_L <= (1 - f) * C_L,max` and its predecessor bracket the crossing, which is interpolated linearly between them. The scan is a single pass, O(n).

**Assumptions.** (1) The polar runs far enough past the peak to bracket the crossing ([[polar-stall]] is swept past the first peak for this purpose). (2) The α spacing resolves the post-peak fall; **this is checked, not assumed** (resolution check below). (3) The polar is the one at the stall Reynolds number — `alpha_break` is only meaningful for the Reynolds number the polar was computed at.

**Resolution check** (maintainer, 2026-10-24: raise the resolution, never loosen a threshold). The crossing is computed a second time from a sweep at **half the published step** (0.125°), from α_S to the end of the range, at the same airplane and at the flow conditions the polar was computed at (speed `V_S`, density, viscosity and speed of sound, carried by the polar value itself) — which is why the entry takes `airplane` besides the polar, and why its tool is the OPT adapter (one more AeroBuildup sweep). The two angles are compared against **one published step, 0.25°**. Basis: linear interpolation between samples cannot be trusted below the sample spacing, so a finer sweep that moves the break by more than one published step shows the grid, not the polar, resolves the value. The tolerance is fixed from the sweep's own step before any measurement; it is a convention, not a sourced number — none exists for a computed polar (adopted by the maintainer, 2026-10-25). A difference above it is a `DesignWarning` of severity *defect* (`stall_break_resolution`) carrying both angles; the value of the published sweep stands.

**Convergence.** None: a single pass with no iteration; the only tolerance is that of the resolution check.

**On failure.** If the polar never falls to `(1 - f) * C_L,max` past `alpha_S` (the event is not bracketed), there is **no value**: the kernel returns a `not_converged` error (an error carries no warning, ARCHITECTURE §8.1) and runs no further sweep. If the sweep at half the step does not bracket the break that the published sweep found, the result is likewise a `not_converged` error. The last sample and the peak sample are never substituted (ADR 0020). On the success path, a resolution check that fails (difference above one published step) is the `DesignWarning` of severity *defect* `stall_break_resolution`, with both angles.

**Dimensional check.** ⚪ procedural — not an algebraic law

**Source.** 🟡 PARTIAL

> **The phenomenon is sourced (🟢):** Anderson, Fundamentals of Aerodynamics 6e, §4.13 (past the stalling angle the lift coefficient falls while the drag rises; leading-edge, trailing-edge and thin-airfoil stall differ in how abruptly), Sadraey, Aircraft Design (2013), §5.4.3 and §5.4.4 (stall and the shape of the lift curve at its maximum), and Lennon, Basics of R/C Model Aircraft Design, Ch. 1–2 (the stall behaviour of model wings). **The quantification is not (🔴):** none of these gives a level or a number for "where the lift curve breaks". The cut level f is a convention adopted on the maintainer's word (2026-10-24, #1219); no published value exists, and the entry says so rather than citing one.

**The source writes it as**

```
Anderson describes the break qualitatively and distinguishes stall types rather than giving a measurement rule.
```

**Validity in the RC/UAV regime (ADR 0028).** Valid **only at the stall Reynolds number**: the post-peak shape of the lift curve changes strongly with Re in the RC range (chord Re 3·10^4 – 1·10^6). Below Re 7·10^4 the laminar separation bubble dominates the section and the confidence in the result is reduced; the value is still computed and the Re is reported with it. Limitations: AeroBuildup does not model three-dimensional separation, so the break is a feature of the section data carried through the wing-level build-up, not a predicted flight stall; the quantity is wing-level only — **tip stall is a separate, later quantity** and is not covered by this entry.

## Implementations (0)

Legacy implementations: none. Kernel: `aero_kernel/formulas/stall_break.py` (#1226).

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

> **Approved** (maintainer, 2026-10-25). `alpha_break` is the first crossing of `(1 - f)·C_L,max` past
> `alpha_S`, linearly interpolated, with `f` = 0.10 (`stall-break-fraction`, the maintainer's convention of
> 2026-10-24, #1219); `stall-break-width = alpha_break − alpha_S`. The phenomenon is sourced (Anderson
> §4.13), the level is the convention. The resolution check (half-step sweep, tolerance one published
> step, 0.25°) is part of the definition; its tolerance is a convention adopted the same day. Kernel
> `aero_kernel/formulas/stall_break.py` (#1226): BRYAN α_break 14.78°, width 1.58°; JAGUAR 11.07°, 1.14° —
> regression, not validation against flight.
