---
canon: aileron-deflection-required
entry: formula
uncertainty: interval
kind: procedure
tool: OPT
shape: law
status: draft
output: aileron-deflection-required-cruise, aileron-deflection-required-approach
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
tex: \delta_{a,req}:\; L(V,\alpha) = m\,g, \quad C_{roll}\big(V,\alpha,\,\delta_{a,req},\,p_{target}\big) = 0
inputs:
  airplane: airplane
  m: aircraft-mass
  g: gravity
  rho: air-density
  v: null
  p_target: null
outputs: {delta_a_req: null}
# ESCALATED: delta_a validity range — the deflection range in which the method holds is open
# (domain experts consulted).
applications:
  - id: cruise
    bind: {v: cruise-speed-target, p_target: roll-rate-target-cruise}
    produce: {delta_a_req: aileron-deflection-required-cruise}
    given: [roll-rate-target-cruise, cruise-speed-target]
  - id: approach
    bind: {v: approach-speed, p_target: roll-rate-target-approach}
    produce: {delta_a_req: aileron-deflection-required-approach}
    given: [roll-rate-target-approach]
worlds: [aerobuildup, avl]
---

# Aileron deflection a roll-rate target needs

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
solve for alpha, delta_a,req (steady roll at V, roll rate held at the target):   L(V, alpha) = m * g,   C_roll(V, alpha, delta_a,req, p_target,cruise | p_target,app) = 0
evaluated at V = V_cruise,target (when given) and at V = V_app, for each roll-rate target given
```

**Produces** [[aileron-deflection-required-cruise]] · [[aileron-deflection-required-approach]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[cruise-speed-target]] · [[approach-speed]] · [[roll-rate-target-cruise]] · [[roll-rate-target-approach]]

**Kind: a procedure — a closure by a prescribed value.** The steady roll: the rolling moment from the ailerons balances the roll damping, lift carries the weight. One symmetric aileron angle ±δ_a; an up/down differential is not modelled (out of the MVP, maintainer 2026-10-01).

**Superseded (maintainer, 2026-10-14):** every control device is an angle; the stops are never referenced — the canon finds which deflection a wanted roll rate needs.

**Measured against a target.** Its companion [[roll-rate]] gives the roll rate at a given aileron deflection, without a target.

**Two answers per operating point, split over two entries.**
- `p` — the roll rate at the given aileron deflection `δ_a`. A property of the airplane at that angle.
- `δ_a,req` — the aileron deflection a roll-rate target needs ([[aileron-deflection-required]]). If no `δ_a` in the method's validity range reaches the target, the result is the error `unsupported_configuration`, code `no_solution_in_validity_range`, with the range and the roll rate reached at its edge in the detail — a fact, never a clipped angle (A10, ADR 0020).

**The requirement names its speed (A2).** At fixed deflection `pb/2V` is nearly independent of speed, so the roll rate in °/s grows with `V`. "Roll rate at cruise" is the character statement RC pilots make; "roll rate on approach" is the controllability statement where Sadraey sizes the aileron (§12.3.3, Phase C — slowest, fewest °/s per degree). Either requirement may be given; each is checked at its own speed.

**AeroBuildup is adequate here** — unlike for adverse yaw. Aileron rolling moment (section lift from NeuralFoil with the deflection) and roll damping (roll rate in the local onset flow, `aero_buildup.py:719-731`) both come from lift, not from induced drag. AVL can cross-check. Declared limit: NeuralFoil's flap model at large deflections and low Reynolds number is unvalidated, and aileron stall beyond about 25° (Sadraey §12.4.3) is only as good as that model.

**Source.** 🟢 Sadraey §12.4 (aileron design; steady roll from `C_l,δa · δa + C_l,p · pb/2V = 0`), with the rate requirement made scale-free per the domain expert (time-to-bank does not transfer to model scale).
