---
name: default_takeoff_speed_margin_vs_to
kind: constant
unit: dimensionless
cluster: perf-oppoints
user_visible: true
source_status: PARTIAL
---

# Default takeoff margin

**Definition.** Multiplier over takeoff-config stall speed for the takeoff-climb point.

**Value.** `1.25`

**Formula — as the code writes it.**

```
"takeoff_speed_margin_vs_to": 1.25
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:207` — `_default_profile`

**Consumed by.**

- in this graph: [[v_takeoff|takeoff_climb target speed]]
- outside it: `app/services/operating_point_generator_service.py:402`

**Source.** 🟡 PARTIAL

> Sadraey §4.3.4.2: 'V_TO ≈ 1.1 V_s to 1.3 V_s'; Sadraey §9.6.2, Eq. for rotation speed: V_R = (1.1 to 1.3)·V_s
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
V_TO ∈ [1.1, 1.3]·V_S,TO
```

**⚠️ Divergence from the source.** 1.25 sits inside the published range, so the method is sourced — but the specific choice of 1.25 rather than Sadraey's own worked default (V_R ≈ 1.1 V_s, giving CL_R = CL_max/1.21) is not attributable. Do not call this SOURCED for the exact number.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
