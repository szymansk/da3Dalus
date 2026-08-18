---
name: vlm-strip-force-vector
symbol: f_strip
kind: quantity
unit: N
cluster: aero-strips
user_visible: false
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
---

# Per-strip force vector

**Definition.** Sum of the panel force vectors belonging to one chordwise strip, in geometry axes.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
f_strip = forces[sl].sum(axis=0)
```

**Inputs.**

- [[vlm-strip-index-ranges|Panel index ranges per strip]]  — *⊣ limit*

**Produced by.** `app/services/vlm_strip_forces.py:258` — `compute_vlm_strip_forces`

**Consumed by.**

- in this graph: `Strip drag force` · `Strip lift force`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> AVL 3.40 source, Avl/src/aero.f:340-358 (strip force accumulated from its chordwise vortex elements: CFX/CFY/CFZ += DCFX/DCFY/DCFZ); AeroSandbox aerostructural tutorial (vlm.forces_geometry indexed per panel)
>
> — via `avl-advisor, aerosandbox-expert`

**The source states it as.**

```
F_strip = sum over the strip's chordwise panels of F_panel
```

**Cited in the code itself.** `app/services/vlm_strip_forces.py:258`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
