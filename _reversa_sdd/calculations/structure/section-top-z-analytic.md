---
name: section-top-z-analytic
symbol: top_z
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
  - flag/divergence
---

# Section upper surface height (analytic)

**Definition.** World-frame z of the upper surface at (y/span, x/c), from the analytic root-to-tip airfoil blend. Ordered so top_z is always the higher of the two surfaces.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
top_z=max(top_z, bottom_z),
```

**Inputs.**

- [[y-span-to-segment|Span fraction to segment mapping]]  — *⊣ limit*

**Produced by.** `cad_designer/airplane/geometry/section_geometry.py:362` — `SectionGeometry._analytic_point`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Contained band upper bound` · `Section mid-height (analytic)` · `Section thickness (analytic)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cad_designer/airplane/geometry/spar_solver.py:763` · `app/services/section_geometry_service.py:55`

**Source.** 🟡 PARTIAL

> RC-Network Wiki / rcplanedesigner, wing__airfoils.md §"Relative Thickness"; Sadraey, Aircraft Design (Wiley 2013), Eq. (7.26) (section thickness from t/c and chord)
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
The definition of an airfoil's upper surface is standard; no source read gives the root-to-tip linear blend used here.
```

**⚠️ Divergence from the source.** The linear root↔tip blend is justified in the code by the loft being ruled (an internal CAD property), not by literature. That justification is geometric and sound, but it is not a citable design method.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `Because the loft is ruled, this linear root↔tip blend equals the built section. Twist / dihedral / sweep are baked into the segment workplanes, so they appear in the placement exactly as for the slice.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
