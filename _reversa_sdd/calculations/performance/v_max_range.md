---
name: v_max_range
kind: quantity
unit: m/s
cluster: perf-oppoints
user_visible: true
source_status: PARTIAL
---

# max_range target speed

**Definition.** Speed assigned to the maximum-range operating point.

**Formula — as the code writes it.**

```
"velocity": max(1.25 * refs["vs_clean"], cruise * 0.95)
```

**Inputs.** [[vs_clean|Clean stall speed reference]] · [[cruise_speed_resolved|Resolved cruise speed]]

**Produced by.** `app/services/operating_point_generator_service.py:458` — `_build_target_definitions`

**Consumed by.**

- outside it: `app/models/analysismodels.py (velocity)`

**Source.** 🟡 PARTIAL

> Sadraey §4.2.5.2 (Breguet range, prop, Eq. 4.17): 'optimum range is achieved when the aircraft flies at the minimum-drag speed, which is the L/D-maximum condition' — i.e. V_maxrange = V_md
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
V_R = V_md = sqrt(2(W/S)/(rho·sqrt(C_D0/K)))
```

**⚠️ Divergence from the source.** The correct quantity is V_md, which the app already computes and caches as v_md_mps. The code instead uses max(1.25·V_s, 0.95·cruise), a second, unsourced producer of a user-visible speed that V_md already owns (ADR 0022). Both multipliers unsourced.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Max-range speed is V_md (max L/D) physically; here it is 1.25·V_s / 0.95·V_cruise, a second, inconsistent producer of the same user-visible quantity while v_md_mps exists in the cached context (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
