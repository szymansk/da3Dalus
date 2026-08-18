---
name: section-bottom-z-analytic
symbol: bottom_z
kind: quantity
unit: mm
cluster: structure
user_visible: true
source_status: PARTIAL
---

# Section lower surface height (analytic)

**Definition.** World-frame z of the lower surface at (y/span, x/c), from the analytic airfoil blend.

**Formula — as the code writes it.**

```
bottom_z=min(top_z, bottom_z),
```

**Inputs.** [[y-span-to-segment|Span fraction to segment mapping]]

**Produced by.** `cad_designer/airplane/geometry/section_geometry.py:363` — `SectionGeometry._analytic_point`

**Consumed by.**

- in this graph: [[band-lo|Contained band lower bound]] · [[section-center-z-analytic|Section mid-height (analytic)]] · [[section-thickness-analytic|Section thickness (analytic)]]
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
