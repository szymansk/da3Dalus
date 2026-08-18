---
name: vlm-panels-per-segment
symbol: counts[i]
kind: quantity
unit: panels
cluster: aero-strips
user_visible: false
source_status: PARTIAL
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/partial
  - flag/divergence
  - solver-adjacent/vlm
---

# Panels allotted to a wing segment

**Definition.** Spanwise panel count for one segment, proportional to its span with a floor.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
[max(min_per_segment, int(round(budget * s / total))) for s in spans]
```

**Inputs.**

- [[vlm-segment-span|Dihedral-inclusive segment span]]
- [[vlm-spanwise-panels-per-half|Spanwise panel budget per half-wing]]
- [[vlm-min-panels-per-segment|Minimum panels per wing segment]]  — *⊣ limit*

**Produced by.** `app/services/vlm_strip_forces.py:74` — `_panels_per_segment`

**Consumed by.**

- in this graph: `Inserted-section blend fraction`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/vlm_strip_forces.py:remesh_uniform_density`

**Source.** 🟡 PARTIAL

> AVL 3.40 User Primer, avl_doc.txt L1097-1108 (Rule 2)
>
> — via `avl-advisor`

**The source states it as.**

```
'Spanwise vortex spacings should be smooth, with no sudden changes in spanwise strip width'
```

**⚠️ Divergence from the source.** Span-proportional allocation delivers a uniform panel DENSITY, which satisfies the smoothness half of Rule 2. It does not satisfy the second half — Rule 2 also demands bunching at taper/dihedral breaks and especially at wingtips, which uniform density never produces.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:74`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
