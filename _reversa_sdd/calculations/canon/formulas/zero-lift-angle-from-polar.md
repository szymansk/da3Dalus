---
canon: zero-lift-angle-from-polar
entry: formula
kind: optimization
tool: OPT
shape: single
status: approved
output: zero-lift-angle-best-glide, lift-curve-slope-best-glide, zero-lift-angle-minimum-sink, lift-curve-slope-minimum-sink
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/single
  - kind/optimization
  - status/approved
tex: \begin{aligned}\alpha_0 = \text{solve}_{\alpha}\; & C_L(V,\alpha) = 0, \qquad C_{L\alpha} = \left.\tfrac{\partial C_L}{\partial \alpha}\right|_{V,\,\alpha_0}\end{aligned}
inputs: {airplane: airplane, v: null, rho: air-density, mu: dynamic-viscosity, a: speed-of-sound}
outputs: {alpha_0: null, cl_alpha: null}
applications:
  - id: best_glide
    bind: {v: minimum-drag-speed}
    produce: {alpha_0: zero-lift-angle-best-glide, cl_alpha: lift-curve-slope-best-glide}
  - id: minimum_sink
    bind: {v: minimum-sink-speed}
    produce: {alpha_0: zero-lift-angle-minimum-sink, cl_alpha: lift-curve-slope-minimum-sink}
---

# Zero-lift angle and lift-curve slope from the computed polar

**Canonical form**

```
alpha_0  := root over alpha of  C_L(V, alpha) = 0       # AeroBuildup inside asb.Opti
C_Lalpha := dC_L/dalpha at (V, alpha_0)                 # exact, by automatic differentiation of the same model
```

**Produces** [[zero-lift-angle-best-glide]] · [[lift-curve-slope-best-glide]] · [[zero-lift-angle-minimum-sink]] · [[lift-curve-slope-minimum-sink]]  ·  **from** [[airplane]] · [[minimum-drag-speed]] · [[minimum-sink-speed]] · [[air-density]] · [[dynamic-viscosity]] · [[speed-of-sound]]

**Kind: an optimisation problem (a root of the lift curve).** α is the one decision variable, solved by
IPOPT through `asb.Opti` with AeroBuildup inside the constraint `C_L(V, α) = 0`, at the speed of the
application. The slope is then the exact derivative `dC_L/dα` of the same AeroBuildup model at the solved
point, per radian, by automatic differentiation (CasADi) of the model function the solve used (#1336), never a
finite difference: a finite difference needs a step, and AeroSandbox's step is a constant the canon does not
own (maintainer 2026-11-01). Approval asks, on top of
source and scale: **no bound active at the solution**, and **what is returned when the solver fails**:
never a value.

**Why a solve, not a straight line through one point (maintainer, 2026-10-31).** These two numbers were
outputs of [[aerobuildup-evaluation]], which is one evaluation at the caller's `(V, α)`. Read off that
one point with `α_0 = α − C_L/C_Lα`, they depend on where the caller happens to evaluate, because the
computed lift curve is not linear there. Measured on BRYAN at 8 m/s, sea level:
- **Slope at 4°:** `C_Lα` = 4.48 /rad, against 5.29 /rad at the zero-lift point.
- **Straight line through 4°:** gives `α_0` = −7.2°.
- **The root:** −3.6°.

The root of `C_L` is a property of the aircraft at that speed. A sweep would give the same root, but it
needs a range and a step the canon does not have. The solve needs neither: no constant beyond IPOPT's own.
Measured cost: about 6 s per solve, of which 3.3 s build the symbolic AeroBuildup model. Since #1336 a
worker reuses that model across solves of the same airplane, so a repeat solve costs about 1–2 s.

**Why two applications, at `V_md` and `V_mp`.** The zero-lift angle moves with the Reynolds number:
- BRYAN, sea level: −3.6° at 8 m/s, −4.3° at 12 m/s, −5.3° at 20 m/s.

So the zero-lift angle has no single value. Each application binds the speed of one optimum,
[[minimum-drag-speed-from-polar]] and [[minimum-sink-speed-from-polar]], so its α_0 and C_Lα hold at that
optimum's Reynolds number. A Reynolds-dependent quantity carries its condition in its name (STAND §2).

**Readers.** No canon formula reads these four quantities. They are characteristics of the lift curve
that a designer requests, e.g. for the wing incidence. Their former reader, the Probe
`linear-lift-curve-inverse`, was deleted (maintainer, 2026-11-01): once α_0 and C_Lα are exact at the
zero-lift root, its mismatch against the optimum α measured only the curvature of the computed curve. No rule
judged that number, and the Probe would have needed a bound of the linear range that has no source.

**Configuration.** The clean airplane as given (`airplane`), all devices as the geometry states them.
Mass and load factor do not enter: the root of `C_L` is independent of the weight.

### The procedure

**Relation solved.** The zero-lift angle of attack `α_L=0`, the intercept of the lift curve
`C_L = C_Lα (α − α_0)`. Anderson §4.3 and §5.3.3 define it for the section and the finite wing. At zero lift
there is no downwash, so `α_0` is unaffected by aspect ratio; `C_Lα` is what AR changes. Sadraey §5.4.3 and
Scholz 08_HighLift §8.2 name `α_0` and `C_Lα` as defining features of the lift curve.

**Method.** IPOPT (interior-point Newton) through `asb.Opti`, one variable α:
- **Start:** 0°.
- **Bounds:** no fixed angle range is imposed (ARCHITECTURE §8.11: a linear relation is solved directly).
  If the adapter needs bounds for IPOPT, then a bound active at the solution is a `not_converged` error,
  as for the other Opti formulas.
- **Iterations:** the same limit as the other Opti adapters.
- **Measured:** BRYAN solved in 3 iterations with a residual `|C_L|` of 1·10⁻⁹.

**Assumptions.** The lift curve has a root in the attached-flow range. That holds for any airplane that
flies, because `C_L` > 0 at the minimum-drag point and `C_L` < 0 at a sufficiently negative α. The root is
the one nearest 0°: a second root on the negative-stall branch lies far from the start.

**Convergence.** IPOPT's own criterion (`tol` = 1·10⁻⁸). On failure, or at an active bound: `not_converged`
with the solver status. The slope is returned only together with a converged root.

**The slope.** `C_Lα` is evaluated by automatic differentiation of the AeroBuildup model function with
respect to α at `(V, α_0)`: the derivative of the very model whose root was solved, exact to rounding, with no
step size and no second AeroBuildup run.

**Dimensional check.** ⚪ procedural, not an algebraic law.

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §4.3 (zero-lift angle `α_L=0`, lift slope `a_0`) and §5.3.3
> (finite-wing `C_L = a (α − α_L=0)`; `α_L=0` independent of AR). The method is AeroBuildup (Sharpe 2024,
> §5.3) inside IPOPT, as for [[stall-speed]] and [[minimum-drag-speed-from-polar]].

**Validity in the RC/UAV regime (ADR 0028).** The tool limits of [[aerobuildup-evaluation]] apply:
- NeuralFoil free-transition polar, `n_crit` = 9;
- reduced confidence near Re_c ≈ 8·10⁴.

At `C_L` = 0 the wing is far from the bubble-sensitive high-lift region, so the root is the most robust
point of the polar. Mach ≤ 0.3.

## Implementations (0)

None in aero_kernel yet.

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

> **Approved** (maintainer, 2026-11-01), with the slope `C_Lα` by automatic differentiation of the model
> function instead of AeroBuildup's finite-difference stability derivative (option a): no step size the canon
> does not own, no second run, and the slope of the very model whose root was solved. This is the relation the
> implementations are measured against.
