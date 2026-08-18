---
name: vlm-n-spanwise
symbol: n_spanwise
kind: quantity
unit: strips
cluster: aero-strips
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/divergence
---

# Spanwise strip count per surface

**Definition.** Number of strips actually assigned to a surface.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
"n_spanwise": len(strips),
```

**Inputs.**

- [[vlm-wing-strip-counts|Expected strips per wing]]

**Produced by.** `app/services/vlm_strip_forces.py:305` — `compute_vlm_strip_forces`

**Consumed by.**

- outside it: `app/schemas/strip_forces.py:SurfaceStripForces.n_spanwise`

**Source.** 🟡 PARTIAL

> AVL 3.40 source, Avl/src/aoutput.f:211 ('# Spanwise' per surface)
>
> — via `avl-advisor`

**⚠️ Divergence from the source.** Reporting convention, not a computed quantity.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:305`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
