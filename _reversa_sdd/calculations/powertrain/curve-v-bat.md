---
name: curve-v-bat
symbol: V_bat
kind: quantity
unit: V
cluster: powertrain
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/sourced
  - audit/confirmed
---

# Battery voltage used for the curve

**Definition.** Loaded pack voltage entering the RPM and power-ceiling calculations.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
V_bat = battery.nominal_voltage_v  # cells × 3.7 V
```

**Inputs.**

- [[battery-nominal-voltage|Nominal pack voltage]]

**Produced by.** `app/services/powertrain_performance.py:640` — `compute_performance_curve`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Electrical power ceiling` · `Fixed operating RPM (non-QPROP branch)` · `Motor terminal voltage`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
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
