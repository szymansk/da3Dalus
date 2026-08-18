---
name: grams-to-kg-divisor
symbol: 1000
kind: constant
unit: dimensionless (unit conversion)
cluster: mass
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/mass
  - class/unclassified-constant
  - source/partial
  - audit/confirmed
---

# g → kg divisor

**Definition.** Unit conversion from the gram-based component tree to the kilogram-based design-assumption store.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `1000.0`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/component_tree_service.py:403` — `get_aircraft_total_weight_kg`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Aircraft total weight from component tree`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/component_tree_service.py:403`

**Source.** 🟡 PARTIAL

> SI prefix definition (1 kg = 1000 g), verified by hand. No consulted aircraft-design source states it; Sadraey §10.4 addresses units only to the extent of noting his equations are valid in SI (m, kg/m³, m², N) or British units.
>
> — via `aircraft-design-scholz`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
