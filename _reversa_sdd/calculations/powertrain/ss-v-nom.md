---
name: ss-v-nom
symbol: V_nom
kind: quantity
unit: V
cluster: powertrain
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/sourced
  - surface/user-visible
---

# Pack nominal voltage (solution space)

**Definition.** Nominal pack voltage for a candidate cell count.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
v_nom = s * CELL_V_NOM
```

**Inputs.**

- [[cell-v-nom|Nominal cell voltage (solution space)]]  — *× unit*
- [[ss-cell-counts|Evaluated cell counts]]

**Produced by.** `app/services/powertrain_solution_space_service.py:134` — `_per_cell`

**Consumed by.**

- in this graph: `Minimum battery capacity` · `Approximate required motor KV`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:142` · `app/services/powertrain_solution_space_service.py:159` · `frontend/components/workbench/PowertrainTab.tsx:569`

**Source.** 🟢 SOURCED

> RC-Network Wiki, 'Nennspannung': multi-cell LiPo packs are rated by multiplying 3.7 V per cell by the cell count ('3 x 3.7 = 11.1 V'). Roxxy Motoren-Fibel Ch. 1, pp. 15-16 on cell count as the RPM-target selector.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
V_nom = S x 3.7 V
```

**Cited in the code itself.** `schema: "Nominal pack voltage [V] = S × 3.7"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
