---
name: cad-shape-own-weight-volume
symbol: m_volume
kind: quantity
unit: g
cluster: mass
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/mass
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# CAD shape own weight — solid print

**Definition.** Own weight of a 'cad_shape' node printed solid: shape volume times material density.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
node.volume_mm3 * density / 1e6 * node.scale_factor
```

**Inputs.**

- [[mm3-density-to-grams-divisor|mm³·(kg/m³) → g divisor]]  — *× unit*
- [[node-scale-factor|Node weight scale factor]]

**Produced by.** `app/services/component_tree_service.py:457` — `_weight_from_cad_shape`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Node own weight`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/component_tree_service.py:470 (_calculate_own_weight)` · `app/services/component_tree_service.py:106` · `app/services/component_tree_service.py:401` · `frontend/components/workbench/ComponentTree.tsx:101`

**Source.** 🟢 SOURCED

> Sadraey, M.H., Wiley 2013, §10.4, source #1 of the four sources of the component weight equations: "Direct relationship between weight and average density — for any object, mass = volume × density." Material density table: Sadraey Table 10.6.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
m = V · ρ  (Sadraey §10.4); in the full weight equation W = (geometry) · ρ_mat · K_ρ · (ratios)^exp · g
```

**⚠️ Divergence from the source.** Sadraey pairs mass = volume × density with a MANDATORY empirical density factor K_ρ, tabulated per component and per aircraft category, precisely because a raw density×volume result is physically wrong for a built-up structure. The code carries K_ρ as node.scale_factor with default 1.0 (app/models/component_tree.py:61) and no table — so the default path is the uncalibrated calculation Sadraey explicitly rules out. node.quantity is also not applied here (component_tree_service.py:457).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** node.quantity is not applied here either (see cad-shape-own-weight-surface).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
