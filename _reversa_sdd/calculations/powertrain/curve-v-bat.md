---
name: curve-v-bat
symbol: V_bat
kind: quantity
unit: V
cluster: powertrain
user_visible: false
source_status: SOURCED
---

# Battery voltage used for the curve

**Definition.** Loaded pack voltage entering the RPM and power-ceiling calculations.

**Formula — as the code writes it.**

```
V_bat = battery.nominal_voltage_v  # cells × 3.7 V
```

**Inputs.** [[battery-nominal-voltage|Nominal pack voltage]]

**Produced by.** `app/services/powertrain_performance.py:640` — `compute_performance_curve`

**Consumed by.**

- in this graph: [[curve-p-available-elec|Electrical power ceiling]] · [[curve-prop-rpm|Fixed operating RPM (non-QPROP branch)]] · [[curve-v-terminal|Motor terminal voltage]]
- outside it: `app/services/powertrain_performance.py:643` · `app/services/powertrain_performance.py:656` · `app/services/powertrain_performance.py:702`

**Source.** 🟢 SOURCED

> RC-Network Wiki, 'Nennspannung': LiPo rated voltage 3.7 V/cell, pack rating = per-cell voltage x cell count.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
V_pack = n_cells x 3.7 V
```

**Cited in the code itself.** `docstring step 1: "Battery voltage: V_bat = cells × 3.7 V (loaded nominal, not peak)"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
