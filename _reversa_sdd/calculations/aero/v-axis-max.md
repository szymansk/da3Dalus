---
name: v-axis-max
kind: quantity
unit: m/s
cluster: aero-spanwise
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Speed-polar X-axis upper bound

**Definition.** Recommended chart upper speed bound from V_dive, else the fastest polar point.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
v_axis_max: float | None = 1.3 * v_dive   /   v_axis_max = max(all_v) if all_v else None
```

**Inputs.**

- [[v-dive-from-context|Dive speed from context]]  — *⊣ limit*
- [[v-axis-max-factor|Upper axis-bound factor]]  — *⊣ limit*
- [[speed-polar-v|Glide forward speed]]

**Produced by.** `app/services/analysis_service.py:561` — `_compute_speed_polar`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Axis-bound sanity guard`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `SpeedPolar.v_axis_max` · `frontend/lib/speedPolarLayout.ts`

**Source.** 🟡 PARTIAL

> Derived from V_dive; V_dive itself is unsourced in this cluster.

**⚠️ Divergence from the source.** Fallback branch (max of all polar V) is a pure display rule.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
