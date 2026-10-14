---
canon: roll-rate
entry: formula
uncertainty: interval
kind: procedure
tool: OPT
shape: law
status: draft
output: roll-rate-approach, roll-rate-nondimensional-approach
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
tex: L(V,\alpha) = m\,g, \quad C_{roll}\big(V,\alpha,\,\delta_a,\,p\big) = 0
inputs:
  airplane: airplane
  m: aircraft-mass
  g: gravity
  rho: air-density
  v_app: approach-speed
  b_ref: wing-span
  delta_a: aileron-deflection
outputs: {p: roll-rate-approach, p_hat: roll-rate-nondimensional-approach}
preconditions:
  - {id: aileron_deflection_within_method_validity, parameter: delta_a, on_violation: warning}
# ESCALATED: delta_a validity range — the deflection range in which the method holds is open
# (domain experts consulted).
worlds: [aerobuildup, avl]
---

# Roll rate at the given aileron deflection

> **Uncertain quantity (A11, maintainer 2026-10-03).** Interval over two method worlds, each run through
> the whole entry: **AeroBuildup** (the optimisation as written below; viscous flap model, but strip-wise
> roll damping without induced relief, strongly nonlinear at real roll rates) and **AVL** (steady roll with
> the ailerons driven directly, `d1 d1 delta`, CLAF by ASB's thickness rule; carries the induced relief
> but no low-Re flap losses). Neither is provably conservative. BRYAN, approach, ailerons ±20°:
> p·b/2V AeroBuildup 0.339, AVL 0.276 (`reference_fleet/bryan_roll_rate_compare.py`). The 23 % spread
> can flip "target met" (A9), so A11 rule 5 makes it an interval. ASB's VLM models no control deflection
> and is not a world.

**Canonical form**

```
solve for alpha, p (steady roll at V, at the given aileron deflection):   L(V, alpha) = m * g,   C_roll(V, alpha, delta_a, p) = 0
evaluated at V = V_app;   p_hat = p * b_ref / (2 * V_app)
```

**Produces** [[roll-rate-approach]] · [[roll-rate-nondimensional-approach]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[approach-speed]] · [[wing-span]] · [[aileron-deflection]]

**Kind: a procedure — a closure by a prescribed value.** The steady roll: the rolling moment from the ailerons balances the roll damping, lift carries the weight. One symmetric aileron angle ±δ_a; an up/down differential is not modelled (out of the MVP, maintainer 2026-10-01).

**Superseded (maintainer, 2026-10-14):** every control device is an angle; the stops are never referenced — the canon finds which deflection a wanted roll rate needs.

**A property of the airplane — no target involved.** Its companion [[aileron-deflection-required]] measures a target against the same steady roll.

**Two answers per operating point, split over two entries.**
- `p` — the roll rate at the given aileron deflection `δ_a`. A property of the airplane at that angle.
- `δ_a,req` — the aileron deflection a roll-rate target needs ([[aileron-deflection-required]]). If no `δ_a` in the method's validity range reaches the target, the result is the error `unsupported_configuration`, code `no_solution_in_validity_range`, with the range and the roll rate reached at its edge in the detail — a fact, never a clipped angle (A10, ADR 0020).

**The requirement names its speed (A2).** At fixed deflection `pb/2V` is nearly independent of speed, so the roll rate in °/s grows with `V`. "Roll rate at cruise" is the character statement RC pilots make; "roll rate on approach" is the controllability statement where Sadraey sizes the aileron (§12.3.3, Phase C — slowest, fewest °/s per degree). Either requirement may be given; each is checked at its own speed.

**AeroBuildup is adequate here** — unlike for adverse yaw. Aileron rolling moment (section lift from NeuralFoil with the deflection) and roll damping (roll rate in the local onset flow, `aero_buildup.py:719-731`) both come from lift, not from induced drag. AVL can cross-check. Declared limit: NeuralFoil's flap model at large deflections and low Reynolds number is unvalidated, and aileron stall beyond about 25° (Sadraey §12.4.3) is only as good as that model.

**Source.** 🟢 Sadraey §12.4 (aileron design; steady roll from `C_l,δa · δa + C_l,p · pb/2V = 0`), with the rate requirement made scale-free per the domain expert (time-to-bank does not transfer to model scale).

**2026-10-02:** evaluated on approach only; the cruise value moved to
[[roll-rate-cruise-target]] and exists only when a cruise-speed target is given. New output
`p_hat_max = p·b/2V` — nearly independent of speed, the RC character statement without a reference
speed.
