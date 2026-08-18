---
name: vlm-blend-twist
symbol: twist
kind: quantity
unit: deg
cluster: aero-strips
user_visible: false
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
---

# Blended section twist

**Definition.** Linear interpolation of geometric twist for an inserted cross-section.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
float(xa.twist) * a + float(xb.twist) * b
```

**Inputs.**

- [[vlm-blend-fraction|Inserted-section blend fraction]]  — *⊣ limit*

**Produced by.** `app/services/vlm_strip_forces.py:112` — `_blend_xsec`

**Consumed by.**

- outside it: `app/services/vlm_strip_forces.py:remesh_uniform_density`

**Source.** 🟢 SOURCED

> AVL 3.40 User Primer, avl_doc.txt L583-633 (SECTION: Ainc incidence linearly interpolated between sections)
>
> — via `avl-advisor`

**The source states it as.**

```
Ainc linear between sections
```

**Cited in the code itself.** `app/services/vlm_strip_forces.py:112`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
