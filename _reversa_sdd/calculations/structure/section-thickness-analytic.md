---
name: section-thickness-analytic
kind: quantity
unit: mm
cluster: structure
user_visible: true
source_status: SOURCED
---

# Section thickness (analytic)

**Definition.** Vertical (world-z) extent of the built section at the chord location — the depth available for a spar before clearance.

**Formula — as the code writes it.**

```
thickness=abs(top_z - bottom_z),
```

**Inputs.** [[section-top-z-analytic|Section upper surface height (analytic)]] · [[section-bottom-z-analytic|Section lower surface height (analytic)]]

**Produced by.** `cad_designer/airplane/geometry/section_geometry.py:361` — `SectionGeometry._analytic_point`

**Consumed by.**

- in this graph: [[station-clearance|Station packing clearance]]
- outside it: `cad_designer/airplane/geometry/spar_solver.py:759` · `cad_designer/airplane/geometry/spar_solver.py:761` · `cad_designer/airplane/geometry/section_geometry.py:398` · `app/services/section_thickness.py:85` · `app/services/section_geometry_service.py:54`

**Source.** 🟢 SOURCED

> RC-Network Wiki / rcplanedesigner, wing__airfoils.md §"Relative Thickness" — "Relative thickness is the ratio between the airfoil's maximum thickness and its chord length"; Sadraey, Aircraft Design: A Systems Engineering Approach (Wiley 2013), §7.9.3, Eq. (7.26); RC-Network Wiki, "Holm", https://wiki.rc-network.de/wiki/Holm (available wing depth is the spar's structural resource)
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
Sadraey Eq. (7.26): t_r = (t/C)_max_r · C_r. The section's vertical extent is the depth available to a spar.
```

**⚠️ Divergence from the source.** The code measures the depth at the SPAR's chord location rather than at maximum thickness, which is the physically correct refinement of Eq. (7.26) for this purpose (Eq. 7.26 gives the maximum). Not an error — a more precise quantity than the source's.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** ```thickness`` is the vertical (world-z) extent between the surfaces and ``center_z`` their midpoint — matching the solid-slice semantics.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
