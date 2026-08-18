---
name: vlm-blend-xyz-le
symbol: xyz_le
kind: quantity
unit: m
cluster: aero-strips
user_visible: false
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
  - solver-adjacent/vlm
---

# Blended section leading-edge point

**Definition.** Linear interpolation of the leading-edge point of an inserted cross-section.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
np.asarray(xa.xyz_le, dtype=float) * a + np.asarray(xb.xyz_le, dtype=float) * b
```

**Inputs.**

- [[vlm-blend-fraction|Inserted-section blend fraction]]  — *⊣ limit*

**Produced by.** `app/services/vlm_strip_forces.py:110` — `_blend_xsec`

**Consumed by.**

- outside it: `app/services/vlm_strip_forces.py:remesh_uniform_density`

**Source.** 🟢 SOURCED

> AVL 3.40 User Primer, avl_doc.txt L583-633 (SECTION keyword: surface is a straight-line loft between consecutive sections); AeroSandbox tutorial 06 VLM point analysis
>
> — via `avl-advisor, aerosandbox-expert`

**The source states it as.**

```
Leading edge Xle,Yle,Zle varies linearly between consecutive SECTIONs
```

**Cited in the code itself.** `app/services/vlm_strip_forces.py:110`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
