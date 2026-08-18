---
name: volts-per-cell-sizing
symbol: 3.7
kind: constant
unit: V/cell
cluster: powertrain
user_visible: false
source_status: SOURCED
node_class: unclassified-constant
tags:
  - cluster/powertrain
  - class/unclassified-constant
  - source/sourced
  - flag/anomaly
---

# Volts per cell (sizing)

**Definition.** Nominal LiPo cell voltage used to derive pack voltage from cell count in the sizing sweep.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `3.7`

**Formula — as the code writes it.**

```
voltage = cells * 3.7
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_sizing_service.py:226` — `_evaluate_motor_battery_combo`

**Consumed by.**

- in this graph: `Resolved battery voltage (sizing)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_sizing_service.py:228`

**Source.** 🟢 SOURCED

> RC-Network Wiki, 'Nennspannung' (wiki.rc-network.de/wiki/Nennspannung), rated-voltage table: LiIo/LiPo = 3.7 V per cell.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
V_cell,nominal = 3.7 V (LiPo)
```

**⚠️ Anomaly.** Bare literal duplicating _VOLTS_PER_LIPO_CELL (powertrain_performance.py:50) and CELL_V_NOM (powertrain_solution_space_service.py:68) — three declarations of the same constant.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# derive from cell count (3.7 V/cell nominal)`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
