---
name: v_takeoff
kind: quantity
unit: m/s
cluster: perf-oppoints
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-oppoints
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# takeoff_climb target speed

**Definition.** Speed of the takeoff-climb operating point.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
takeoff = float(goals.get("takeoff_speed_margin_vs_to", 1.25)) * refs["vs_to"]
```

**Inputs.**

- [[default_takeoff_speed_margin_vs_to|Default takeoff margin]]  — *⤵ fallback*
- [[vs_to|Takeoff-config stall speed reference]]

**Produced by.** `app/services/operating_point_generator_service.py:402` — `_build_target_definitions`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/operating_point_generator_service.py:417`

**Source.** 🟡 PARTIAL

> Sadraey §4.3.4.2 (V_TO ≈ 1.1–1.3 V_s) and §9.6.2 (V_R = 1.1–1.3 V_s)
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
V_TO ∈ [1.1, 1.3]·V_S,TO
```

**⚠️ Divergence from the source.** 1.25 is inside the range; the exact value is not attributable. Sadraey's own worked takeoff cases use V_R ≈ 1.1 V_s (CL_R = CL_max/1.21).

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
