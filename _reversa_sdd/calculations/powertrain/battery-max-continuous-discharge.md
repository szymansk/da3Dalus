---
name: battery-max-continuous-discharge
symbol: P_battery_max
kind: quantity
unit: W
cluster: powertrain
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
---

# Battery maximum continuous discharge power

**Definition.** Continuous electrical power the pack can deliver, from capacity times C-rate times nominal voltage. Returns +inf when no C-rate is known.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if self.c_rate is None: return float("inf") ; capacity_ah = self.capacity_mah / 1000.0 ; return capacity_ah * self.c_rate * self.nominal_voltage_v
```

**Inputs.**

- [[battery-capacity-mah-input|Battery capacity]]
- [[battery-c-rate-input|Battery C-rate]]
- [[battery-nominal-voltage|Nominal pack voltage]]

**Produced by.** `app/services/powertrain_performance.py:195` — `BatterySpec.max_continuous_discharge_w`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Electrical power ceiling`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:650`

**Source.** 🟡 PARTIAL

> RC-Network Wiki, 'Nennspannung' supplies the 3.7 V/cell nominal voltage. The C-rate definition (I_max = C x capacity_Ah) is standard battery-industry terminology; no consulted expert source states it with a citable section.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
P = capacity_Ah x C x V_nom
```

**Cited in the code itself.** `docstring: "P = capacity_ah × C-rate × V_nominal"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
