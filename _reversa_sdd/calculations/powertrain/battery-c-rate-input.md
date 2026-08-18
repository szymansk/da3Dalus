---
name: battery-c-rate-input
symbol: c_rate
kind: parameter
unit: 1/h (C)
cluster: powertrain
user_visible: true
source_status: PARTIAL
---

# Battery C-rate

**Definition.** Discharge rating multiple of capacity.

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_performance.py:179` — `BatterySpec.c_rate`

**Consumed by.**

- in this graph: [[battery-max-continuous-discharge|Battery maximum continuous discharge power]] · [[battery-max-current|Battery maximum continuous discharge current]]
- outside it: `app/services/powertrain_performance.py:195` · `app/services/powertrain_performance.py:202`

**Source.** 🟡 PARTIAL

> Standard battery-industry terminology (discharge rate as a multiple of rated capacity). Not defined in any of the three expert vaults consulted (Sadraey/Scholz, Anderson, rcplanedesigner/RC-Network/Roxxy/Drela).
>
> — via `rc-aircraft-designer`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
