---
name: fe_n_neg_maneuver
symbol: n-
kind: quantity
unit: g
cluster: perf-envelope
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/divergence
---

# Negative maneuver load factor

**Definition.** Achievable negative load factor, clipped at -0.4 times the positive g-limit.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
n_neg = max(q * wing_area_m2 * cl_min / weight, -0.4 * g_limit)
```

**Inputs.**

- [[fe_q|Dynamic pressure]]
- [[fe_wing_area|Reference wing area]]  — *× unit*
- [[fe_cl_min|Inverted maximum lift coefficient]]  — *⊣ limit*
- [[fe_weight|Aircraft weight]]
- [[fe_g_limit|Structural limit load factor]]  — *⤵ fallback*
- [[fe_neg_g_factor|Negative g-limit ratio]]  — *⊣ limit*

**Produced by.** `app/services/flight_envelope_service.py:328` — `compute_vn_curve`

**Consumed by.**

- outside it: `VnDiagram.tsx`

**Source.** 🟡 PARTIAL

> Construction per FAR 23.333(b)/CS-VLA 333(b); clip per Sadraey §10.4.1 / FAR 23.337(b)(1).
>
> — via `scholz`

**The source states it as.**

```
n_neg = max(q*S*CL_min/W, -0.4*n_lim)
```

**⚠️ Divergence from the source.** Compounds two unvalidated constants (-0.8 CL ratio, -0.4 g ratio) into one user-visible curve.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
