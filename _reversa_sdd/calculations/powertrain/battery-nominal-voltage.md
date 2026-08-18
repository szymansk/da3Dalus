---
name: battery-nominal-voltage
symbol: V_bat
kind: quantity
unit: V
cluster: powertrain
user_visible: true
source_status: SOURCED
---

# Nominal pack voltage

**Definition.** Loaded nominal pack voltage at 3.7 V per cell.

**Formula — as the code writes it.**

```
return self.cells * _VOLTS_PER_LIPO_CELL
```

**Inputs.** [[battery-cells-input|Battery cell count]] · [[volts-per-lipo-cell|Loaded LiPo cell voltage]]

**Produced by.** `app/services/powertrain_performance.py:184` — `BatterySpec.nominal_voltage_v`

**Consumed by.**

- in this graph: [[battery-max-continuous-discharge|Battery maximum continuous discharge power]] · [[curve-v-bat|Battery voltage used for the curve]]
- outside it: `app/services/powertrain_performance.py:195` · `app/services/powertrain_performance.py:640`

**Source.** 🟢 SOURCED

> RC-Network Wiki, 'Nennspannung': LiIo/LiPo rated voltage 3.7 V per cell; 'Multi-cell packs are rated by multiplying the per-cell voltage by cell count. For example, a 3-cell LiPo pack is rated at 3 x 3.7 = 11.1 V.'
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
V_pack = n_cells x 3.7 V
```

**⚠️ Anomaly.** Uses nominal 3.7 V/cell where the solution-space module uses a sag voltage of 3.5 V/cell for the same physical quantity under load (powertrain_solution_space_service.py:69) — two different pack-voltage models across the cluster.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `docstring: "Nominal pack voltage [V] at 3.7 V/cell (loaded)."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
