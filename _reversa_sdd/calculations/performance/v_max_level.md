---
name: v_max_level
kind: quantity
unit: m/s
cluster: perf-oppoints
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/perf-oppoints
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Maximum level speed target

**Definition.** Target speed for the max_level_speed operating point.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
v_max_level = float(goals.get("max_level_speed_mps") or max(1.35 * cruise, cruise + 8.0))
```

**Inputs.**

- [[default_max_level_speed_mps|Default maximum level speed]]  — *⤵ fallback*
- [[cruise_speed_resolved|Resolved cruise speed]]

**Produced by.** `app/services/operating_point_generator_service.py:399` — `_build_target_definitions`

**Consumed by.**

- outside it: `app/services/operating_point_generator_service.py:466 (max_level_speed target)` · `app/services/assumption_compute_service.py:1038`

**Source.** 🟡 PARTIAL

> Sadraey §4.3.3.2: 'V_max ≈ 1.2–1.3 V_C if only cruise speed is specified (cruise is performed at 75–80 % power)'
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
V_max = (1.2 … 1.3) · V_C
```

**⚠️ Divergence from the source.** The multiplicative fallback is the right form but 1.35 is above the published 1.2–1.3 band. The additive branch (cruise + 8.0 m/s) has no source at all and is dimensionally arbitrary — it makes V_max/V_C range from 1.8 (at V_C = 10) to 1.3 (at V_C = 27), i.e. the rule silently changes character across the RC/UAV size range.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The fallback 1.35× / +8 m/s pair is a magic number with no cited source.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
