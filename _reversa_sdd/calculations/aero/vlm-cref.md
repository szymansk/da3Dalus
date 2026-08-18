---
name: vlm-cref
symbol: Cref
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

# Reference chord echoed to the response

**Definition.** Airplane reference chord, also the denominator of cl_norm.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
c_ref = float(asb_airplane.c_ref)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/vlm_strip_forces.py:216` — `compute_vlm_strip_forces`

**Consumed by.**

- in this graph: `Normalised strip lift coefficient`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/analysis_service.py:_build_strip_forces_response (Reynolds)` · `frontend/hooks/useStripForces.ts`

**Source.** 🟢 SOURCED

> AVL 3.40 User Primer, avl_doc.txt L240-295 (Cref: reference chord, moment normaliser)
>
> — via `avl-advisor`

**The source states it as.**

```
Cref = reference chord (MAC)
```

**Cited in the code itself.** `app/services/vlm_strip_forces.py:216`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
