---
name: vlm-segment-span
symbol: spans[i]
kind: quantity
unit: m
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

# Dihedral-inclusive segment span

**Definition.** True spanwise length of a wing segment including dihedral (y-z distance between xsec LEs).

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
float(math.hypot(b[1] - a[1], b[2] - a[2]))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/vlm_strip_forces.py:84` — `_segment_spans`

**Consumed by.**

- in this graph: `Panels allotted to a wing segment`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/vlm_strip_forces.py:remesh_uniform_density`

**Source.** 🟡 PARTIAL

> AVL 3.40 source, Avl/src/aoutput.f:305 (ASTRP = WSTRIP(J)*CHORD(J), WSTRIP = strip width measured along the surface)
>
> — via `avl-advisor`

**⚠️ Divergence from the source.** Using the dihedral-inclusive y-z length matches AVL's WSTRIP convention (strip width follows the surface, not its y-projection). Consistent, but the choice is not documented in the app and the same code echoes b_ref, which is the PROJECTED span — two different span conventions in one response.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:84`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
