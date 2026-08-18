---
name: s_obstacle_factor_apply
symbol: s_obstacle
kind: quantity
unit: m
cluster: perf-matching
user_visible: true
source_status: PARTIAL
---

# Obstacle-corrected distance

**Definition.** Ground roll scaled by an obstacle-clearance factor.

**Formula — as the code writes it.**

```
return k * s_ground
```

**Inputs.** [[s_to_ground|Takeoff ground roll]] · [[s_ldg_ground|Landing ground roll]] · [[k_to_50ft|Takeoff 50-ft obstacle factor]] · [[k_ldg_50ft|Landing 50-ft obstacle factor]]

**Produced by.** `app/services/field_length_service.py:142` — `_apply_obstacle_factor`

**Consumed by.**

- outside it: `s_to_50ft:419,425` · `s_ldg_50ft:436`

**Source.** 🟡 PARTIAL

> Applying a multiplicative ground-roll-to-obstacle factor is standard preliminary-design practice, but neither Scholz 05_PreliminarySizing §5.1-5.2 nor Sadraey §4.3.2/4.3.4 uses this structure: Sadraey's Eq. 4.66 absorbs the airborne section into the coefficient 1.65 inside the log form, and Scholz/Loftin correlates the total field length directly.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
Sadraey Eq. 4.66 constant 1.65 'absorbs the integration of the ground roll plus the airborne section to the obstacle'
```

**⚠️ Divergence from the source.** The multiply-afterwards structure is the code's own; the sources fold the air phase into the primary correlation. Consequently the two factors (1.66, 2.73) are not interchangeable with anything in the literature.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `"Apply obstacle correction factor: s_obstacle = k · s_ground."`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
