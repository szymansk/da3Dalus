---
name: v_stall_near_clean
kind: quantity
unit: m/s
cluster: perf-oppoints
user_visible: true
source_status: SOURCED
---

# stall_near_clean target speed

**Definition.** Speed of the near-stall clean operating point.

**Formula — as the code writes it.**

```
stall_near = float(goals.get("min_speed_margin_vs_clean", 1.20)) * refs["vs_clean"]
```

**Inputs.** [[default_min_speed_margin_vs_clean|Default clean stall margin]] · [[vs_clean|Clean stall speed reference]]

**Produced by.** `app/services/operating_point_generator_service.py:401` — `_build_target_definitions`

**Consumed by.**

- outside it: `app/services/operating_point_generator_service.py:410 (target velocity)`

**Source.** 🟢 SOURCED

> Lennon, Basics of R/C Model Aircraft Design (1996), Ch. 4 — 20 % margin over stall; Scholz 05_PreliminarySizing §5.4 — V₂ = 1.2·V_S,TO (CS 25.107)
>
> — via `rc-aircraft-designer, aircraft-design-scholz`

**The source states it as.**

```
V = 1.20 · V_S1
```

**⚠️ Divergence from the source.** Form and value both match. See default_min_speed_margin_vs_clean.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
