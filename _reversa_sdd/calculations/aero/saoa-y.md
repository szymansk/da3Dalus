---
name: saoa-y
symbol: y_m
kind: quantity
unit: m
cluster: aero-strips
user_visible: true
source_status: PARTIAL
---

# Panel spanwise position

**Definition.** y-coordinate of each LiftingLine vortex centre.

**Formula — as the code writes it.**

```
y_arr = np.array(ll.vortex_centers)[:, 1]
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/section_aoa_service.py:271` — `compute_section_aoa`

**Consumed by.**

- in this graph: [[bwsd-airfoil-per-section|Per-section airfoil name]] · [[bwsd-section-area-raw|Raw trapezoidal section area]] · [[cdftp-frac|Span fraction of a section]] · [[cdftp-y-span|Span extent for trip interpolation]] · [[saoa-alpha-l0-at-y|Interpolated zero-lift angle at panel y]] · [[saoa-twist-at-y|Interpolated twist at panel y]]
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
