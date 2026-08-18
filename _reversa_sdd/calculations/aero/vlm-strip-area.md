---
name: vlm-strip-area
symbol: Area
kind: quantity
unit: m²
cluster: aero-strips
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/divergence
  - solver-adjacent/vlm
---

# Strip area

**Definition.** Sum of the panel areas in one chordwise strip.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
area = float(areas[sl].sum())
```

**Inputs.**

- [[vlm-strip-index-ranges|Panel index ranges per strip]]  — *⊣ limit*

**Produced by.** `app/services/vlm_strip_forces.py:259` — `compute_vlm_strip_forces`

**Consumed by.**

- in this graph: `Local strip drag coefficient` · `Local strip lift coefficient` · `Surface total area`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/schemas/strip_forces.py:StripForceEntry.area` · `app/services/spanwise_loads.py:58` · `frontend/hooks/useStripForces.ts`

**Source.** 🟢 SOURCED

> AVL 3.40 source, Avl/src/aoutput.f:305 (ASTRP = WSTRIP(J) * CHORD(J))
>
> — via `avl-advisor`

**The source states it as.**

```
Area_strip = strip width * local chord (planform)
```

**⚠️ Divergence from the source.** Real. AVL's strip area is width x chord — a PLANFORM area. The code sums the VLM panel areas, which are the actual lofted panel surfaces and therefore include twist/camber inclination. For a twisted or highly cambered strip the app's area exceeds AVL's, so cl and cd (both divided by this area) read systematically low relative to the AVL path filling the same fields.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:259`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
