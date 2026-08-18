---
name: battery-max-current
symbol: I_bat_max
kind: quantity
unit: A
cluster: powertrain
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/partial
  - surface/user-visible
---

# Battery maximum continuous discharge current

**Definition.** Continuous discharge current from capacity times C-rate. Returns +inf when no C-rate is known.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if self.c_rate is None: return float("inf") ; return (self.capacity_mah / 1000.0) * self.c_rate
```

**Inputs.**

- [[battery-capacity-mah-input|Battery capacity]]
- [[battery-c-rate-input|Battery C-rate]]

**Produced by.** `app/services/powertrain_performance.py:202` — `BatterySpec.max_current_a`

**Consumed by.**

- in this graph: `Electrical power ceiling`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:657`

**Source.** 🟡 PARTIAL

> C-rate as a multiple of rated capacity is standard battery terminology; none of the three expert vaults (Sadraey/Scholz, Anderson, rcplanedesigner/RC-Network/Roxxy) states the definition in a citable section.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
I = C x capacity_Ah
```

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
