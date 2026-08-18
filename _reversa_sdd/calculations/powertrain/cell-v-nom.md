---
name: cell-v-nom
symbol: CELL_V_NOM
kind: constant
unit: V/cell
cluster: powertrain
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/powertrain
  - class/unclassified-constant
  - source/sourced
  - surface/user-visible
  - audit/confirmed
---

# Nominal cell voltage (solution space)

**Definition.** Mid-discharge nominal LiPo cell voltage, used for the energy-to-capacity conversion and the KV estimate.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `3.7`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_solution_space_service.py:68` — `CELL_V_NOM`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Pack nominal voltage (solution space)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
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
