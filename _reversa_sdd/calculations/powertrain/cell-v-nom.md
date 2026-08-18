---
name: cell-v-nom
symbol: CELL_V_NOM
kind: constant
unit: V/cell
cluster: powertrain
user_visible: true
source_status: SOURCED
---

# Nominal cell voltage (solution space)

**Definition.** Mid-discharge nominal LiPo cell voltage, used for the energy-to-capacity conversion and the KV estimate.

**Value.** `3.7`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_solution_space_service.py:68` — `CELL_V_NOM`

**Consumed by.**

- in this graph: [[ss-v-nom|Pack nominal voltage (solution space)]]
- outside it: `app/services/powertrain_solution_space_service.py:134`

**Source.** 🟢 SOURCED

> RC-Network Wiki, 'Nennspannung': LiIo/LiPo rated voltage 3.7 V per cell, defined as 'the nominal voltage measured during discharge under typical operating current'.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
V_cell,nom = 3.7 V
```

**Cited in the code itself.** `# V  nominal (mid-discharge)`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
