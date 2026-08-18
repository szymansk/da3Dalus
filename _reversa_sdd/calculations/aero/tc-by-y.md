---
name: tc-by-y
symbol: t/c
kind: quantity
unit: -
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/divergence
---

# Local thickness-to-chord ratio

**Definition.** Built section thickness divided by the station's own chord, both in millimetres.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
tc_by_y[y_m] = thickness_mm / chord_mm
```

**Inputs.**

- [[chord-mm-by-y|Station chord in millimetres]]

**Produced by.** `app/services/analysis_service.py:2259` — `_get_tc_by_y_for_surface`

**Consumed by.**

- in this graph: `Per-surface spar sizing block`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `compute_spar_sizing` · `SparSizingResult`

**Source.** 🟢 SOURCED

> Scholz 07_WingDesign §7.1 (Wing Sections and Airfoil Scaling) and §7.4 (Wing Box and Structural Spars)
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
t_section(x) = t_airfoil(x)·c(y);  (t/c)_section = (t/c)_airfoil;  bending stiffness EI ∝ h³
```

**⚠️ Divergence from the source.** None — dividing the built section thickness by the station's own chord is exactly the source's definition. Both operands are in mm so the ratio is dimensionless and correct.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
