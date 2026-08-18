---
name: combo-flight-time-min
symbol: estimated_flight_time_min
kind: quantity
unit: min
cluster: powertrain
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/partial
  - surface/user-visible
---

# Estimated flight time

**Definition.** Endurance in minutes, the primary ranking metric of the sizing sweep.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
flight_time_min = flight_time_h * 60
```

**Inputs.**

- [[combo-flight-time-h|Estimated flight time (hours)]]

**Produced by.** `app/services/powertrain_sizing_service.py:257` — `_evaluate_motor_battery_combo`

**Consumed by.**

- in this graph: `Combo confidence`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_sizing_service.py:268` · `app/services/powertrain_sizing_service.py:271` · `frontend/components/workbench/PowertrainSizingModal.tsx:200`

**Source.** 🟡 PARTIAL

> Unit conversion of combo-flight-time-h only; see that entry.
>
> — via `aircraft-design-scholz`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
