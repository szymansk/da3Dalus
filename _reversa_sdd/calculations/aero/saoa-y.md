---
name: saoa-y
symbol: y_m
kind: quantity
unit: m
cluster: aero-strips
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
  - solver-adjacent/liftingline
---

# Panel spanwise position

**Definition.** y-coordinate of each LiftingLine vortex centre.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
y_arr = np.array(ll.vortex_centers)[:, 1]
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/section_aoa_service.py:271` — `compute_section_aoa`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Per-section airfoil name` · `Raw trapezoidal section area` · `Span fraction of a section` · `Span extent for trip interpolation` · `Interpolated zero-lift angle at panel y` · `Interpolated twist at panel y`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/api/v2/endpoints/section_aoa.py:SectionAoaPoint.y_m` · `app/services/turbulator_optimizer_service.py:build_wing_section_data` · `frontend/hooks/useSectionAoa.ts`

**Source.** 🟡 PARTIAL

> AeroSandbox docs_aero_3d.md, LiftingLine (spanwise discretisation into sections, each with its own local aerodynamics)
>
> — via `aerosandbox-expert`

**⚠️ Divergence from the source.** Reading vortex_centers[:,1] is API bookkeeping; note it is the y-coordinate only, so on a dihedral wing it is the PROJECTED station, not the arc-length station.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/section_aoa_service.py:271`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
