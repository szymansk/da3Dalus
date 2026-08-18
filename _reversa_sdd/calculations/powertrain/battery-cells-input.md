---
name: battery-cells-input
symbol: cells (S)
kind: parameter
unit: cells (S)
cluster: powertrain
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: unclassified-parameter
tags:
  - cluster/powertrain
  - class/unclassified-parameter
  - source/sourced
  - surface/user-visible
  - audit/confirmed
---

# Battery cell count

**Definition.** LiPo series cell count of the selected pack.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_performance.py:177` — `BatterySpec.cells`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Nominal pack voltage`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:184`

**Source.** 🟢 SOURCED

> RC-Network Wiki, 'Nennspannung': multi-cell packs rated by cell count x 3.7 V. Roxxy Motoren-Fibel, Ch. 1, pp. 15-16: 'Battery cell count (3S, 4S, 5S, etc.) directly sets the no-load RPM target, scaled by the motor's KV value.'
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
V_pack = S x 3.7 V ;  RPM_no-load = KV x V_pack
```

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
