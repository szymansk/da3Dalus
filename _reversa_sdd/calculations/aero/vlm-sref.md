---
name: vlm-sref
symbol: Sref
kind: quantity
unit: m²
cluster: aero-strips
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/divergence
---

# Reference area echoed to the response

**Definition.** Airplane reference area copied straight from the (un-remeshed) ASB airplane.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
s_ref = float(asb_airplane.s_ref)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/vlm_strip_forces.py:215` — `compute_vlm_strip_forces`

**Consumed by.**

- outside it: `app/services/analysis_service.py:_build_strip_forces_response` · `frontend/hooks/useStripForces.ts`

**Source.** 🟢 SOURCED

> AVL 3.40 User Primer, avl_doc.txt L240-295 (Sref: reference area for all force coefficients)
>
> — via `avl-advisor`

**The source states it as.**

```
Sref = wing reference (planform) area
```

**⚠️ Divergence from the source.** Definition matches. What is not sourced is which wing supplies it: asb_airplane.s_ref is whatever the converter set, and section_aoa_service picks the first symmetric wing while turbulator_optimizer_service picks the largest — three different resolutions of one defined quantity.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:215`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
