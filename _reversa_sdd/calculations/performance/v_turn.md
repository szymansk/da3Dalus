---
name: v_turn
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

# Turn target speed

**Definition.** Speed used for all three default bank-angle turn points.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
"velocity": max(cruise, 1.3 * refs["vs_clean"])
```

**Inputs.**

- [[cruise_speed_resolved|Resolved cruise speed]]
- [[vs_clean|Clean stall speed reference]]

**Produced by.** `app/services/operating_point_generator_service.py:493` — `_build_target_definitions`

**Consumed by.**

- outside it: `app/services/operating_point_generator_service.py:1154 (_apply_turn_feasibility)` · `app/services/add_turn_service.py:58`

**Source.** 🟡 PARTIAL

> Sadraey §12.3.1 (speed-range definitions per MIL-F-8785C): 'Low: 1.3 V_s ≤ V < 1.8 V_s (take-off, approach)' — 1.3 V_s is the lower edge of the band where handling-quality requirements are specified
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** 1.3·V_s is a recognisable boundary in the source, but the source never proposes it as a *turn* speed. A steady turn at bank phi needs V ≥ V_s·sqrt(1/cos phi); at 60° bank that is 1.41·V_s, so max(cruise, 1.3·V_s) is below the stall boundary for the 60° point whenever cruise is low — the code then flags STALL_IN_TURN on a target it generated itself. The same 1.3 is independently hardcoded in add_turn_service.py:58.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The same 1.3 factor appears independently at add_turn_service.py:58 — two producers of the default turn speed.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
