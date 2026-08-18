---
name: v-axis-min
kind: quantity
unit: m/s
cluster: aero-spanwise
user_visible: true
source_status: PARTIAL
---

# Speed-polar X-axis lower bound

**Definition.** Recommended chart lower speed bound.

**Formula — as the code writes it.**

```
v_axis_min: float | None = 0.7 * min(v_stall_values)
```

**Inputs.** [[v-stall|Stall speed]] · [[v-axis-min-factor|Lower axis-bound factor]]

**Produced by.** `app/services/analysis_service.py:556` — `_compute_speed_polar`

**Consumed by.**

- in this graph: [[axis-autorange-guard|Axis-bound sanity guard]]
- outside it: `SpeedPolar.v_axis_min` · `frontend/lib/speedPolarLayout.ts`

**Source.** 🟡 PARTIAL

> Derived from V_stall (Sadraey §4.3.2 Eq. 4.30), which is sourced; the axis bound itself is a display decision.

**⚠️ Divergence from the source.** The quantity it scales is sourced; the 0.7 factor is not.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
