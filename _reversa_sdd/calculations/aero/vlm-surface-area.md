---
name: vlm-surface-area
symbol: surface_area
kind: quantity
unit: m²
cluster: aero-strips
user_visible: true
source_status: PARTIAL
---

# Surface total area

**Definition.** Sum of strip areas assigned to one surface.

**Formula — as the code writes it.**

```
surface_area += area
```

**Inputs.** [[vlm-strip-area|Strip area]]

**Produced by.** `app/services/vlm_strip_forces.py:268` — `compute_vlm_strip_forces`

**Consumed by.**

- outside it: `app/schemas/strip_forces.py:SurfaceStripForces.surface_area` · `frontend/hooks/useStripForces.ts`

**Source.** 🟡 PARTIAL

> AVL 3.40 source, Avl/src/aoutput.f:211 (Surface area Ssurf reported per surface)
>
> — via `avl-advisor`

**⚠️ Divergence from the source.** Summing strip areas per surface mirrors AVL's Ssurf. Inherits the panel-vs-planform area difference noted under vlm-strip-area.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:257,268`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
