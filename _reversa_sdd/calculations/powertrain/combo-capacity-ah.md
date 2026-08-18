---
name: combo-capacity-ah
symbol: capacity_ah
kind: quantity
unit: Ah
cluster: powertrain
user_visible: false
source_status: PARTIAL
---

# Battery capacity in amp-hours

**Definition.** Rated pack capacity converted from mAh.

**Formula — as the code writes it.**

```
capacity_ah = capacity_mah / 1000.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_sizing_service.py:255` — `_evaluate_motor_battery_combo`

**Consumed by.**

- in this graph: [[combo-flight-time-h|Estimated flight time (hours)]]
- outside it: `app/services/powertrain_sizing_service.py:256`

**Source.** 🟡 PARTIAL

> Unit conversion mAh -> Ah only. RC-Network Wiki 'Motorsteller' confirms mAh is the RC convention for pack capacity.
>
> — via `rc-aircraft-designer`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
