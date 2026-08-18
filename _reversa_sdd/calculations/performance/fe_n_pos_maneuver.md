---
name: fe_n_pos_maneuver
symbol: n+
kind: quantity
unit: g
cluster: perf-envelope
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/scale
---

# Positive maneuver load factor

**Definition.** Aerodynamically achievable positive load factor, clipped at the structural g-limit.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
n_pos = min(q * wing_area_m2 * cl_max / weight, g_limit)
```

**Inputs.**

- [[fe_q|Dynamic pressure]]
- [[fe_wing_area|Reference wing area]]  — *× unit*
- [[fe_cl_max|Maximum lift coefficient (envelope)]]  — *⤵ fallback*
- [[fe_weight|Aircraft weight]]
- [[fe_g_limit|Structural limit load factor]]  — *⤵ fallback*

**Produced by.** `app/services/flight_envelope_service.py:327` — `compute_vn_curve`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `VnDiagram.tsx`

**Source.** 🟢 SOURCED

> Standard manoeuvring-envelope construction, FAR 23.333(b) / CS-VLA 333(b).
>
> — via `scholz`

**The source states it as.**

```
n = q*S*CL_max/W, clipped at n_lim
```

**⚠️ Scale (ADR 0023).** Correct construction; its output inherits fe_g_limit's unvalidated 3.0 clip (see fe_g_limit).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
