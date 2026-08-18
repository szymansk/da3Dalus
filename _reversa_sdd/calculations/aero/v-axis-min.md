---
name: v-axis-min
kind: quantity
unit: m/s
cluster: aero-spanwise
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/divergence
---

# Speed-polar X-axis lower bound

**Definition.** Recommended chart lower speed bound.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
v_axis_min: float | None = 0.7 * min(v_stall_values)
```

**Inputs.**

- [[v-stall|Stall speed]]  — *⊣ limit*
- [[v-axis-min-factor|Lower axis-bound factor]]  — *⊣ limit*

**Produced by.** `app/services/analysis_service.py:556` — `_compute_speed_polar`

**Consumed by.**

- in this graph: `Axis-bound sanity guard`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `SpeedPolar.v_axis_min` · `frontend/lib/speedPolarLayout.ts`

**Source.** 🟡 PARTIAL

> Derived from V_stall (Sadraey §4.3.2 Eq. 4.30), which is sourced; the axis bound itself is a display decision.

**⚠️ Divergence from the source.** The quantity it scales is sourced; the 0.7 factor is not.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
