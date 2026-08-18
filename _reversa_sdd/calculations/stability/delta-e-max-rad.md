---
name: delta-e-max-rad
symbol: δe_max
kind: quantity
unit: rad
cluster: stability
user_visible: false
source_status: SOURCED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
---

# Maximum elevator deflection (radians)

**Definition.** Maximum trailing-edge-up elevator deflection, always positive.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return abs(float(negative_deflection_deg)) * math.pi / 180.0
```

**Inputs.**

- [[default-delta-e-deg|Default maximum elevator deflection]]  — *⤵ fallback*

**Produced by.** `app/services/elevator_authority_service.py:123` — `_delta_e_max_rad`

**Consumed by.**

- in this graph: `Elevator authority (finite difference)` · `TE-UP deflection command` · `Net nose-up moment coefficient`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/elevator_authority_service.py:236,310,611,709,754,787,821,1016,1060,1097,1128,1158`

**Source.** 🟢 SOURCED

> Unit conversion of the sourced deflection limit (Sadraey §12.5.5 step 4, 25° typical). Radian measure is required because control derivatives are per-radian (Sadraey §12.5.2, C_mδE in 1/rad).
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
δ_E [rad] = δ_E [deg] · π/180
```

**Cited in the code itself.** `Amendment B3: δe_max = abs(negative_deflection_deg) * π/180`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
