---
name: section-bottom-z-analytic
symbol: bottom_z
kind: quantity
unit: mm
cluster: structure
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
---

# Section lower surface height (analytic)

**Definition.** World-frame z of the lower surface at (y/span, x/c), from the analytic airfoil blend.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
bottom_z=min(top_z, bottom_z),
```

**Inputs.**

- [[y-span-to-segment|Span fraction to segment mapping]]  — *⊣ limit*

**Produced by.** `cad_designer/airplane/geometry/section_geometry.py:363` — `SectionGeometry._analytic_point`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Contained band lower bound` · `Section mid-height (analytic)` · `Section thickness (analytic)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cad_designer/airplane/geometry/spar_solver.py:762` · `app/services/section_geometry_service.py:56`

**Source.** 🟡 PARTIAL

> RC-Network Wiki / rcplanedesigner, wing__airfoils.md §"Relative Thickness"; Sadraey, Aircraft Design (Wiley 2013), Eq. (7.26)
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
Standard airfoil surface definition; the blend is a CAD property, not a literature method.
```

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
