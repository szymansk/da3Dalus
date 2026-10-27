---
canon: roll-due-to-yaw-rate-mp
kind: quantity
symbol: C_l_r,mp
unit: 1/rad
role: output
tags:
  - canon/quantity
  - discipline/lateral
  - stage/stability-structure
  - role/output
type: scalar
---

# Roll due to yaw rate at the minimum-sink speed · `C_l_r,mp`

Rolling-moment derivative with the non-dimensional yaw rate `r̂ = r·b/(2V)`; positive for a normal aircraft: a yawing aircraft rolls towards the turn.

**Unit.** `1/rad` (the convention of [[spiral-criterion-mp]], which multiplies it with `C_n_beta` in `1/rad`; `r̂` itself is dimensionless).

**Produced by.** [[lateral-static-stability-mp]] — an output added by maintainer decision 2026-10-27, #1275 (the same AVL run already yields it for the spiral criterion).

**Authority.** AVL for every layout, not validated (K27, 2026-10-05); evaluated at the circling condition V_mp (#1309).

**Used by.** [[turn-sideslip]]
