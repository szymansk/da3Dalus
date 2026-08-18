---
name: battery-cells-input
symbol: cells (S)
kind: parameter
unit: cells (S)
cluster: powertrain
user_visible: true
source_status: SOURCED
---

# Battery cell count

**Definition.** LiPo series cell count of the selected pack.

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_performance.py:177` — `BatterySpec.cells`

**Consumed by.**

- in this graph: [[battery-nominal-voltage|Nominal pack voltage]]
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
