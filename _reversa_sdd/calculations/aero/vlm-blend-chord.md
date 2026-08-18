---
name: vlm-blend-chord
symbol: chord
kind: quantity
unit: m
cluster: aero-strips
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
  - audit/confirmed
  - solver-adjacent/vlm
---

# Blended section chord

**Definition.** Linear interpolation of chord for an inserted cross-section.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
float(xa.chord) * a + float(xb.chord) * b
```

**Inputs.**

- [[vlm-blend-fraction|Inserted-section blend fraction]]  — *⊣ limit*

**Produced by.** `app/services/vlm_strip_forces.py:111` — `_blend_xsec`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/vlm_strip_forces.py:remesh_uniform_density`

**Source.** 🟢 SOURCED

> AVL 3.40 User Primer, avl_doc.txt L583-633 (SECTION: Chord linearly interpolated between sections)
>
> — via `avl-advisor`

**The source states it as.**

```
Chord linear between sections
```

**Cited in the code itself.** `app/services/vlm_strip_forces.py:111`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
