---
name: vlm-strip-le
symbol: le
kind: quantity
unit: m
cluster: aero-strips
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
  - surface/user-visible
  - solver-adjacent/vlm
---

# Strip leading-edge point

**Definition.** Midpoint of the front-left/front-right vertices of the strip's first panel.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
le = 0.5 * (fl[lo] + fr[lo])
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/vlm_strip_forces.py:260` — `compute_vlm_strip_forces`

**Consumed by.**

- in this graph: `Local strip chord`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `Xle/Yle/Zle output fields` · `app/services/spanwise_loads.py:59 (Yle)` · `frontend/components/workbench/AnalysisViewerPanel.tsx`

**Source.** 🟢 SOURCED

> AVL 3.40 source, Avl/src/aoutput.f:312 (RLE(1..3,J) = strip leading-edge point, reported as Xle/Yle/Zle)
>
> — via `avl-advisor`

**The source states it as.**

```
Xle,Yle,Zle = strip leading-edge reference point
```

**Cited in the code itself.** `app/services/vlm_strip_forces.py:260`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
