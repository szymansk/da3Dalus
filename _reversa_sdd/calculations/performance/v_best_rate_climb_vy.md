---
name: v_best_rate_climb_vy
symbol: Vy
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

# Vy target speed

**Definition.** Speed assigned to the best-rate-of-climb operating point.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
"velocity": max(1.50 * refs["vs_clean"], cruise * 0.95)
```

**Inputs.**

- [[vs_clean|Clean stall speed reference]]
- [[cruise_speed_resolved|Resolved cruise speed]]

**Produced by.** `app/services/operating_point_generator_service.py:434` — `_build_target_definitions`

**Consumed by.**

- outside it: `app/models/analysismodels.py (velocity)`

**Source.** 🟡 PARTIAL

> Sadraey §4.3.5.2, Eq. 4.85: for a PROP-driven aircraft the maximum-ROC speed is the minimum-POWER speed, V_ROCmax = sqrt(2W/(ρ·S·sqrt(3·C_D0/K))) = 0.76·V_md (the 1.155 = sqrt(4/3) factor in Eq. 4.89). Sadraey §4.2.5.4, Eq. 4.25 puts that same speed at ≈1.2–1.4 V_s.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
V_y = V_Pmin = 0.76·V_md ≈ (1.2 … 1.4)·V_s
```

**⚠️ Divergence from the source.** Method is fully sourced; the code's value is not. 1.50·V_s is above Sadraey's 1.2–1.4 band. Worse, for a propeller aircraft V_y and the endurance speed are the SAME physical speed (both = minimum-power speed), yet the code assigns 1.50·V_s here and 1.15·V_s to loiter — a 30 % spread on one quantity. The context already caches a physics-derived V_md that would give the right answer.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Same as Vx: a rate-of-climb optimum labelled from magic multipliers (1.50, 0.95), never from excess power.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
