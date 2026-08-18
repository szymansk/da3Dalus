---
name: section-center-z-analytic
symbol: center_z
kind: quantity
unit: mm
cluster: structure
user_visible: true
source_status: PARTIAL
---

# Section mid-height (analytic)

**Definition.** Midpoint between the upper and lower surfaces — the spar-placement height reference.

**Formula — as the code writes it.**

```
center_z=(top_z + bottom_z) / 2.0,
```

**Inputs.** [[section-top-z-analytic|Section upper surface height (analytic)]] · [[section-bottom-z-analytic|Section lower surface height (analytic)]]

**Produced by.** `cad_designer/airplane/geometry/section_geometry.py:364` — `SectionGeometry._analytic_point`

**Consumed by.**

- in this graph: [[center-z-mm|Section mid-height (spar placement reference)]] · [[station-center-z|Station centre height]]
- outside it: `cad_designer/airplane/geometry/spar_solver.py:775` · `app/services/section_thickness.py:96` · `app/services/section_geometry_service.py:57`

**Source.** 🟡 PARTIAL

> RC-Network Wiki, "Mechanische Spannung (Materialkunde)", https://wiki.rc-network.de/wiki/Mechanische_Spannung — in a beam under bending, "the upper region experiences tension, the lower region experiences compression, while stress in the middle becomes minimal"; Lennon, The Basics of R/C Model Aircraft Design (1996), Ch. 13 (flanges symmetric about the neutral axis)
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
The mid-depth is the neutral-axis reference a symmetric spar is centred on.
```

**⚠️ Divergence from the source.** The sources describe the neutral axis of the SPAR SECTION; the code takes the midpoint of the AIRFOIL section. For a symmetric spar centred in the section these coincide, but for a cambered airfoil the airfoil mid-height is not in general the spar's neutral axis, and no source read addresses that distinction.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
