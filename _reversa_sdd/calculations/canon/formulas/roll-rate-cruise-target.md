---
canon: roll-rate-cruise-target
entry: formula
uncertainty: interval
kind: procedure
tool: OPT
shape: law
status: draft
output: roll-rate-cruise
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
inputs:
  airplane: airplane
  m: aircraft-mass
  g: gravity
  rho: air-density
  v_cruise_target: cruise-speed-target
  delta_a: aileron-deflection
outputs: {p: roll-rate-cruise}
applications:
  - id: at_cruise_speed_target
    given: [cruise-speed-target]
    when: has_aileron
worlds: [aerobuildup, avl]
---

# Roll rate at the mission's cruise speed

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
solve for alpha, p at V_cruise,target (steady roll, at the given aileron deflection):   L = m * g,   C_roll(V, alpha, delta_a, p) = 0
```

**Produces** [[roll-rate-cruise]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[cruise-speed-target]] · [[aileron-deflection]]

**Kind: a procedure**, the same steady roll as [[roll-rate]], evaluated at `V_cruise,target`.
**Only when a cruise-speed target is given** (maintainer, 2026-10-02). Without one, the approach
check and the dimensionless roll rate `p·b/2V` of [[roll-rate]] remain — for an RC model without
a cruise requirement the latter is the character statement, since it hardly depends on speed.

**Method premise (architect, 2026-10-14).** AeroBuildup has no flap model of its own: it evaluates the clean airfoil at `α + τ·δ`, `τ = 1 − x_hinge^2.7514` (a δ-independent fit to an XFoil study), with the drag times a multiplier fitted to Hoerner, *Fluid Dynamic Drag*, p. 13-13 Fig. 32 (`aerosandbox/geometry/airfoil/kulfan_airfoil.py:211-255`, via `aero_buildup.py:784-801`). There is no flap separation: it over-predicts the effectiveness at large δ until the clean section stalls, and the δ range of the τ fit is unknown. AVL is linear in δ by construction and documented only for `|pb/2V| < 0.10`. Reference point: Sadraey §12.4.3 — beyond about 20–25° deflection, flow separates over the aileron and effectiveness drops; recommendation `|δ_A,max| ≤ 25°`. Transport and GA material, not checked at model Reynolds number (ADR 0028). Beyond it the solver adapter reports a warning with the angle; the canon sets no limit.
