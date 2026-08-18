---
name: ss-cap-mah
symbol: cap_mAh
kind: quantity
unit: mAh
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
  - flag/anomaly
  - flag/divergence
---

# Minimum battery capacity

**Definition.** Capacity floor from the energy budget: required energy divided by nominal voltage.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cap_mah = energy_wh / v_nom * 1000.0
```

**Inputs.**

- [[ss-energy-wh|Required mission energy]]
- [[ss-v-nom|Pack nominal voltage (solution space)]]

**Produced by.** `app/services/powertrain_solution_space_service.py:142` — `_per_cell`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Hyperbola capacity samples` · `Hyperbola plot span multiplier` · `Catalog battery match flag` · `Raw required C-rate`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:145` · `app/services/powertrain_solution_space_service.py:426` · `app/services/powertrain_solution_space_service.py:441` · `app/services/powertrain_solution_space_service.py:463` · `frontend/components/workbench/PowertrainTab.tsx:129`

**Source.** 🟡 PARTIAL

> Elementary energy-to-charge conversion (Ah = Wh/V). No consulted expert source states it; Sadraey (2013) §8.7 gives only the coarse anchor that a 2-hp electric motor needs ~400 g of battery for 15 minutes.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
capacity_Ah = E_Wh / V ;  x1000 for mAh
```

**⚠️ Divergence from the source.** Energy is budgeted at V_nom while the current constraint is evaluated at V_sag. RC-Network Wiki 'Nennspannung' defines the rated voltage as the value 'measured during discharge under typical operating current', i.e. one pack has one nominal voltage; modelling the same pack at two voltages makes the capacity floor and the C-rate floor mutually inconsistent.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Energy is budgeted at V_nom while current is drawn at V_sag — the same pack is modelled at two voltages, so capacity and C-rate are not mutually consistent.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `module docstring: "cap_mAh = E_Wh  / V_nom × 1000"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
