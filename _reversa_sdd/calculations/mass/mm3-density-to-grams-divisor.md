---
name: mm3-density-to-grams-divisor
symbol: 1e6
kind: constant
unit: dimensionless (unit conversion)
cluster: mass
user_visible: false
source_status: PARTIAL
---

# mm³·(kg/m³) → g divisor

**Definition.** Unit-conversion divisor: volume in mm³ times density in kg/m³ divided by 1e6 yields mass in grams.

**Value.** `1e6`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/component_tree_service.py:455` — `_weight_from_cad_shape`

**Consumed by.**

- in this graph: [[cad-shape-own-weight-surface|CAD shape own weight — surface print]] · [[cad-shape-own-weight-volume|CAD shape own weight — solid print]]
- outside it: `app/services/component_tree_service.py:455` · `app/services/component_tree_service.py:457`

**Source.** 🟡 PARTIAL

> Dimensional identity, verified by hand, not attributable to any consulted source: 1 mm³ = 1e-9 m³ and 1 kg = 1e3 g, so mm³ · (kg/m³) = 1e-9 kg = 1e-6 g, hence the ÷1e6. No aircraft-design reference states this; it is SI unit algebra. Sadraey §10.4 notes only that his equations are valid in either SI or British units and that g converts mass to force.
>
> — via `aircraft-design-scholz`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
