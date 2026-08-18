---
name: ss-raw-c
symbol: raw_c
kind: quantity
unit: 1/h (C)
cluster: powertrain
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/partial
  - audit/confirmed
---

# Raw required C-rate

**Definition.** Physically required discharge rate before any safety margin: peak current over capacity in Ah.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
raw_c = i_peak / (cap_mah / 1000.0) if cap_mah > 0 else float("inf")
```

**Inputs.**

- [[ss-i-peak|Peak battery current]]
- [[ss-cap-mah|Minimum battery capacity]]  — *⊣ limit*

**Produced by.** `app/services/powertrain_solution_space_service.py:145` — `_per_cell`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Required battery C-rate`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:146`

**Source.** 🟡 PARTIAL

> C-rate as discharge current divided by rated capacity in Ah is standard battery-industry terminology. It is not defined in any of the three expert vaults consulted.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
C = I / capacity_Ah
```

**Cited in the code itself.** `module docstring: "C_min   = I_peak / (cap_mAh / 1000)"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
