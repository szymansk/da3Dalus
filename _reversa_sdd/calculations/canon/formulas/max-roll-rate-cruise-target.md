---
canon: max-roll-rate-cruise-target
entry: formula
uncertainty: interval
kind: procedure
tool: OPT
shape: law
status: draft
output: max-roll-rate-cruise
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
---

# Maximum roll rate at the mission's cruise speed

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
solve for alpha, p_max at V_cruise,target (steady roll, full set throw):   L = m * g,   C_roll(V, alpha, delta_a,max, p_max) = 0
```

**Produces** [[max-roll-rate-cruise]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[cruise-speed-target]]

**Kind: a procedure**, the same steady roll as [[max-roll-rate]], evaluated at `V_cruise,target`.
**Only when a cruise-speed target is given** (maintainer, 2026-10-02). Without one, the approach
check and the dimensionless roll rate `p·b/2V` of [[max-roll-rate]] remain — for an RC model without
a cruise requirement the latter is the character statement, since it hardly depends on speed.
