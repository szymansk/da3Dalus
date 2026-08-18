---
name: vlm-bref
symbol: Bref
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

# Reference span echoed to the response

**Definition.** Airplane reference span passed through to the strip-forces response.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
b_ref = float(asb_airplane.b_ref)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/vlm_strip_forces.py:217` — `compute_vlm_strip_forces`

**Consumed by.**

- outside it: `app/services/analysis_service.py:_build_strip_forces_response` · `frontend/hooks/useStripForces.ts`

**Source.** 🟢 SOURCED

> AVL 3.40 User Primer, avl_doc.txt L240-295 (Bref: reference span)
>
> — via `avl-advisor`

**The source states it as.**

```
Bref = reference span
```

**Cited in the code itself.** `app/services/vlm_strip_forces.py:217`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
