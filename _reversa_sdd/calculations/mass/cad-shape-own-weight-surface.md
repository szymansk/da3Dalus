---
name: cad-shape-own-weight-surface
symbol: m_surface
kind: quantity
unit: g
cluster: mass
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/mass
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# CAD shape own weight — surface print

**Definition.** Own weight of a 'cad_shape' node printed as a shell: printed surface area times print wall resolution times material density.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
node.area_mm2 * resolution * density / 1e6 * node.scale_factor
```

**Inputs.**

- [[print-resolution-default|Default print wall resolution]]  — *⤵ fallback*
- [[mm3-density-to-grams-divisor|mm³·(kg/m³) → g divisor]]  — *× unit*
- [[node-scale-factor|Node weight scale factor]]

**Produced by.** `app/services/component_tree_service.py:455` — `_weight_from_cad_shape`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Node own weight`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/component_tree_service.py:470 (_calculate_own_weight)` · `app/services/component_tree_service.py:106` · `app/services/component_tree_service.py:401` · `frontend/components/workbench/ComponentTree.tsx:101`

**Source.** 🟡 PARTIAL

> Sadraey, M.H., Wiley 2013, §10.4 ("Empirical Weight Calculation Technique Foundations"), source #1 of four: "Direct relationship between weight and average density — for any object, mass = volume × density"; material densities tabulated in Table 10.6 (aerospace aluminium 2711 kg/m³, fiberglass/epoxy 1800–1850 kg/m³, balsa 160 kg/m³).
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
W_component = (geometry term) · ρ_mat · K_ρ · (ratio terms)^exponents · g  (Sadraey §10.4, general form of every component weight equation)
```

**⚠️ Divergence from the source.** Two things are unattributable. (1) The shell idealisation volume = area × t_wall is not stated by any consulted source; Sadraey reaches the same place through a tabulated empirical density factor K_ρ per component, not through a wall thickness. (2) Sadraey's explicit warning applies directly here: "aero-structures are not solid objects but hollow assemblies … a pure density-times-volume calculation would massively overestimate weight, so empirical density factors (K_ρ) reduce the result to physically correct numbers." The code's only K_ρ analogue is node.scale_factor, whose default is 1.0 — i.e. uncalibrated by default. Also: node.quantity is not applied on this branch (component_tree_service.py:455), unlike the COTS branch at :438.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** node.quantity is NOT applied on this branch, while the COTS branch (line 438) multiplies by quantity. A cad_shape node with quantity=3 is counted once — asymmetric handling of the same field.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
