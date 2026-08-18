---
name: mm3-density-to-grams-divisor
symbol: 1e6
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

# mm³·(kg/m³) → g divisor

**Definition.** Unit-conversion divisor: volume in mm³ times density in kg/m³ divided by 1e6 yields mass in grams.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `1e6`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/component_tree_service.py:455` — `_weight_from_cad_shape`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `CAD shape own weight — surface print` · `CAD shape own weight — solid print`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/component_tree_service.py:455` · `app/services/component_tree_service.py:457`

**Source.** 🟡 PARTIAL

> Dimensional identity, verified by hand, not attributable to any consulted source: 1 mm³ = 1e-9 m³ and 1 kg = 1e3 g, so mm³ · (kg/m³) = 1e-9 kg = 1e-6 g, hence the ÷1e6. No aircraft-design reference states this; it is SI unit algebra. Sadraey §10.4 notes only that his equations are valid in either SI or British units and that g converts mass to force.
>
> — via `aircraft-design-scholz`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
