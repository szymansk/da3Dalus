---
name: v-axis-max
kind: quantity
unit: m/s
cluster: aero-spanwise
user_visible: true
source_status: PARTIAL
---

# Speed-polar X-axis upper bound

**Definition.** Recommended chart upper speed bound from V_dive, else the fastest polar point.

**Formula — as the code writes it.**

```
v_axis_max: float | None = 1.3 * v_dive   /   v_axis_max = max(all_v) if all_v else None
```

**Inputs.** [[v-dive-from-context|Dive speed from context]] · [[v-axis-max-factor|Upper axis-bound factor]] · [[speed-polar-v|Glide forward speed]]

**Produced by.** `app/services/analysis_service.py:561` — `_compute_speed_polar`

**Consumed by.**

- in this graph: [[axis-autorange-guard|Axis-bound sanity guard]]
- outside it: `SpeedPolar.v_axis_max` · `frontend/lib/speedPolarLayout.ts`

**Source.** 🟡 PARTIAL

> Derived from V_dive; V_dive itself is unsourced in this cluster.

**⚠️ Divergence from the source.** Fallback branch (max of all polar V) is a pure display rule.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
