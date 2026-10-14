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
preconditions:
  - {id: aileron_deflection_within_method_validity, parameter: delta_a, on_violation: warning}
# ESCALATED: delta_a validity range — the deflection range in which the method holds is open
# (domain experts consulted).
applications:
  - id: at_cruise_speed_target
    given: [cruise-speed-target]
worlds: [aerobuildup, avl]
---

# Roll rate at the mission's cruise speed

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
solve for alpha, p at V_cruise,target (steady roll, at the given aileron deflection):   L = m * g,   C_roll(V, alpha, delta_a, p) = 0
```

**Produces** [[roll-rate-cruise]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[cruise-speed-target]] · [[aileron-deflection]]

**Kind: a procedure**, the same steady roll as [[roll-rate]], evaluated at `V_cruise,target`.
**Only when a cruise-speed target is given** (maintainer, 2026-10-02). Without one, the approach
check and the dimensionless roll rate `p·b/2V` of [[roll-rate]] remain — for an RC model without
a cruise requirement the latter is the character statement, since it hardly depends on speed.
