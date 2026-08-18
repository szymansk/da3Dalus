---
name: motor-max-electrical-power
symbol: P_motor_max_elec
kind: quantity
unit: W
cluster: powertrain
user_visible: true
source_status: PARTIAL
---

# Motor maximum electrical input power (estimated)

**Definition.** Estimated peak electrical input power the motor can absorb, derived from the burst current limit at loaded pack voltage. Explicitly tagged ESTIMATED, not a datasheet value. Returns +inf when max_current_a is unknown.

**Formula — as the code writes it.**

```
if self.max_current_a is None: return float("inf") ; return self.max_current_a * _VOLTS_PER_LIPO_CELL * self.cells_lipo_max
```

**Inputs.** [[motor-max-current-input|Motor burst current limit]] · [[volts-per-lipo-cell|Loaded LiPo cell voltage]] · [[motor-cells-lipo-max-input|Maximum LiPo cell count]]

**Produced by.** `app/services/powertrain_performance.py:159` — `MotorSpec.max_electrical_power_w`

**Consumed by.**

- in this graph: [[curve-p-available-elec|Electrical power ceiling]]
- outside it: `app/services/powertrain_performance.py:649`

**Source.** 🟡 PARTIAL

> RC-Network Wiki, 'Nennspannung' supplies the 3.7 V/cell factor; P = V*I is elementary. No aircraft-design or RC source consulted derives a motor power ceiling as I_burst x V_pack_max.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
P = V * I  (elementary); V_pack = n_cells x 3.7 V (RC-Network Wiki, 'Nennspannung')
```

**⚠️ Divergence from the source.** RC-Network Wiki 'Motorsteller' warns that manufacturers rate CONTINUOUS current and that peak/pulse figures are 'substantially higher than continuous rating'. The code multiplies the burst current by the motor's MAXIMUM supported cell count, compounding two upper bounds into a ceiling that no source supports as a usable power figure.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Uses the motor's MAXIMUM supported cell count, not the cell count of the battery actually selected in the request — so a 3S pack on a 6S-capable motor still yields a 6S power ceiling.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `docstring: "Derived from max_current_a × 3.7 V/cell × cells_lipo_max. Uses loaded 3.7 V/cell, not peak 4.2 V (UAT note, gh-615 comment #3). Tagged as ESTIMATED — not a datasheet-reported value."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
