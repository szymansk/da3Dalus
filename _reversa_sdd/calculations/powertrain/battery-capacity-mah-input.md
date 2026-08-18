---
name: battery-capacity-mah-input
symbol: capacity_mah
kind: parameter
unit: mAh
cluster: powertrain
user_visible: true
source_status: PARTIAL
node_class: unclassified-parameter
tags:
  - cluster/powertrain
  - class/unclassified-parameter
  - source/partial
  - surface/user-visible
---

# Battery capacity

**Definition.** Rated pack capacity.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_performance.py:178` — `BatterySpec.capacity_mah`

**Consumed by.**

- in this graph: `Battery maximum continuous discharge power` · `Battery maximum continuous discharge current`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:194` · `app/services/powertrain_performance.py:202`

**Source.** 🟡 PARTIAL

> RC-Network Wiki 'Motorsteller' references pack capacity as the reference for ESC continuous ratings ('historically 1600 mAh, now variable with modern LiPo packs'). Capacity in mAh is standard RC practice but no consulted source defines it formally.
>
> — via `rc-aircraft-designer`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
