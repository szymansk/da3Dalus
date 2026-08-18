---
name: battery-c-rate-input
symbol: c_rate
kind: parameter
unit: 1/h (C)
cluster: powertrain
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-parameter
tags:
  - cluster/powertrain
  - class/unclassified-parameter
  - source/partial
  - surface/user-visible
  - audit/confirmed
---

# Battery C-rate

**Definition.** Discharge rating multiple of capacity.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_performance.py:179` — `BatterySpec.c_rate`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Battery maximum continuous discharge power` · `Battery maximum continuous discharge current`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:195` · `app/services/powertrain_performance.py:202`

**Source.** 🟡 PARTIAL

> Standard battery-industry terminology (discharge rate as a multiple of rated capacity). Not defined in any of the three expert vaults consulted (Sadraey/Scholz, Anderson, rcplanedesigner/RC-Network/Roxxy/Drela).
>
> — via `rc-aircraft-designer`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
