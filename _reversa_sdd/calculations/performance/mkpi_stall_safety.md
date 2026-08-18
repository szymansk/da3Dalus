---
name: mkpi_stall_safety
symbol: V_cruise / V_s1
kind: quantity
unit: -
cluster: perf-envelope
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/scale
---

# KPI: stall safety

**Definition.** Cruise-to-stall speed ratio; higher means more stall margin.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
value = v_cruise / v_s1
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/mission_kpi_service.py:117` — `_kpi_stall_safety`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `MissionRadarChart.tsx` · `AxisDrawer.tsx`

**Source.** 🟡 PARTIAL

> The ratio-to-stall-speed concept is regulatory: FAR 23.51 / CS-23 require V at 50 ft >= 1.2*V_S1, and FAR 23.73 sets approach V_REF >= 1.3*V_S0. No source defines V_cruise/V_s1 as a mission-compliance metric.
>
> — via `scholz, rc`

**The source states it as.**

```
V_cruise / V_s1
```

**⚠️ Scale (ADR 0023).** The regulatory anchors are takeoff/approach speeds for certified aircraft, not a cruise-based safety index for RC. The KPI's axis bands come from the presets and are the real authority — treat the metric as an app construction, not a regulatory one.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
