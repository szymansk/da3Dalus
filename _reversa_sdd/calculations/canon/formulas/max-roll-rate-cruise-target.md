---
canon: max-roll-rate-cruise-target
entry: formula
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

**Canonical form**

```
solve for alpha, p_max at V_cruise,target (steady roll, full set throw):   L = m * g,   C_roll(V, alpha, delta_a,max, p_max) = 0
```

**Produces** [[max-roll-rate-cruise]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[cruise-speed-target]]

**Kind: a procedure**, the same steady roll as [[max-roll-rate]], evaluated at `V_cruise,target`.
**Only when a cruise-speed target is given** (maintainer, 2026-10-02). Without one, the approach
check and the dimensionless roll rate `p·b/2V` of [[max-roll-rate]] remain — for an RC model without
a cruise requirement the latter is the character statement, since it hardly depends on speed.
