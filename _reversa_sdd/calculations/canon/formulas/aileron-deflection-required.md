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
applications:
  - id: cruise
    bind: {v: cruise-speed-target, p_target: roll-rate-target-cruise}
    produce: {delta_a_req: aileron-deflection-required-cruise}
    given: [roll-rate-target-cruise, cruise-speed-target]
    when: has_aileron
  - id: approach
    bind: {v: approach-speed, p_target: roll-rate-target-approach}
    produce: {delta_a_req: aileron-deflection-required-approach}
    given: [roll-rate-target-approach]
    when: has_aileron
worlds: [aerobuildup, avl]
---

# Aileron deflection a roll-rate target needs

> **Uncertain quantity (A11, maintainer 2026-10-03).** Interval over two method worlds, each run through
> the whole entry: **AeroBuildup** (the optimisation as written below; the deflection as an effective-angle shift `τ·δ` on the clean airfoil with a Hoerner drag factor — no flap separation — and strip-wise
> roll damping without induced relief, strongly nonlinear at real roll rates) and **AVL** (steady roll with
> the ailerons driven directly, `d1 d1 delta`, CLAF by ASB's thickness rule; carries the induced relief
> but no low-Re flap losses). Neither is provably conservative. BRYAN, approach, ailerons ±20°:
> p·b/2V AeroBuildup 0.339, AVL 0.276 (`reference_fleet/bryan_roll_rate_compare.py`). The 23 % spread
> can flip "target met" (A9), so A11 rule 5 makes it an interval. ASB's VLM models no control deflection
> and is not a world.

**AVL world, outside its own stated range (finding #1181).** AVL is linear in δ by construction (`Avl/src/amake.f:1184-1187`, "linearize about zero deflection"), and its primer gives `−0.10 < pb/2V < 0.10` as the practical limit for roll rates, beyond which results "should be interpreted with caution" (`Avl/avl_doc.txt:121-141`). The BRYAN AVL value `pb/2V = 0.276` lies outside it. The interval decision (A11) is unchanged; this is recorded, not resolved.

**Canonical form**

```
solve for alpha, delta_a,req (steady roll at V, roll rate held at the target):   L(V, alpha) = m * g,   C_roll(V, alpha, delta_a,req, p_target,cruise | p_target,app) = 0
evaluated at V = V_cruise,target (when given) and at V = V_app, for each roll-rate target given
world aerobuildup:  search delta_a upward from 0 until p(delta_a) stops increasing; a target above that maximum
                    has no solution in this world (target_above_method_maximum, with the maximum roll rate and
                    its delta_a); never a clipped angle
world avl:          linear in delta; delta_a,req solved directly
```

**Produces** [[aileron-deflection-required-cruise]] · [[aileron-deflection-required-approach]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[cruise-speed-target]] · [[approach-speed]] · [[roll-rate-target-cruise]] · [[roll-rate-target-approach]]

**Kind: a procedure — a closure by a prescribed value.** The steady roll: the rolling moment from the ailerons balances the roll damping, lift carries the weight. One symmetric aileron angle ±δ_a; an up/down differential is not modelled (out of the MVP, maintainer 2026-10-01).

**Superseded (maintainer, 2026-10-14):** every control device is an angle; the stops are never referenced — the canon finds which deflection a wanted roll rate needs.

**Measured against a target.** Its companion [[roll-rate]] gives the roll rate at a given aileron deflection, without a target.

**Two answers per operating point, split over two entries.**
- `p` — the roll rate at the given aileron deflection `δ_a`. A property of the airplane at that angle.
- `δ_a,req` — the aileron deflection a roll-rate target needs ([[aileron-deflection-required]]). In the AeroBuildup world `δ_a` is searched upward from 0 until `p(δ_a)` stops increasing; a target above that maximum has no solution in this world — the error `unsupported_configuration`, code `target_above_method_maximum`, with the maximum roll rate and its `δ_a` in the detail, never a clipped angle (A10, ADR 0020). In the AVL world, linear in δ, `δ_a,req` is solved directly.

**The requirement names its speed (A2).** At fixed deflection `pb/2V` is nearly independent of speed, so the roll rate in °/s grows with `V`. "Roll rate at cruise" is the character statement RC pilots make; "roll rate on approach" is the controllability statement where Sadraey sizes the aileron (§12.3.3, Phase C — slowest, fewest °/s per degree). Either requirement may be given; each is checked at its own speed.

**AeroBuildup is adequate here** — unlike for adverse yaw. Aileron rolling moment (section lift from NeuralFoil on the clean airfoil at `α + τ·δ`) and roll damping (roll rate in the local onset flow, `aero_buildup.py:719-731`) both come from lift, not from induced drag. AVL can cross-check.

**Method premise (architect, 2026-10-14).** AeroBuildup has no flap model of its own: it evaluates the clean airfoil at `α + τ·δ`, `τ = 1 − x_hinge^2.7514` (a δ-independent fit to an XFoil study), with the drag times a multiplier fitted to Hoerner, *Fluid Dynamic Drag*, p. 13-13 Fig. 32 (`aerosandbox/geometry/airfoil/kulfan_airfoil.py:211-255`, via `aero_buildup.py:784-801`). There is no flap separation: it over-predicts the effectiveness at large δ until the clean section stalls, and the δ range of the τ fit is unknown. AVL is linear in δ by construction and documented only for `|pb/2V| < 0.10`. Reference point: Sadraey §12.4.3 puts separation onset on a deflected surface at about 20–25° — transport and GA data, not checked at model Reynolds number (ADR 0028). Beyond it the solver adapter reports a warning with the angle; the canon sets no limit.

**Source.** 🟢 Sadraey §12.4 (aileron design; steady roll from `C_l,δa · δa + C_l,p · pb/2V = 0`), with the rate requirement made scale-free per the domain expert (time-to-bank does not transfer to model scale).
