---
name: grams-to-kg-divisor
symbol: 1000
kind: constant
unit: dimensionless (unit conversion)
cluster: mass
user_visible: false
source_status: PARTIAL
---

# g → kg divisor

**Definition.** Unit conversion from the gram-based component tree to the kilogram-based design-assumption store.

**Value.** `1000.0`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/component_tree_service.py:403` — `get_aircraft_total_weight_kg`

**Consumed by.**

- in this graph: [[aircraft-total-weight-kg|Aircraft total weight from component tree]]
- outside it: `app/services/component_tree_service.py:403`

**Source.** 🟡 PARTIAL

> SI prefix definition (1 kg = 1000 g), verified by hand. No consulted aircraft-design source states it; Sadraey §10.4 addresses units only to the extent of noting his equations are valid in SI (m, kg/m³, m², N) or British units.
>
> — via `aircraft-design-scholz`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
