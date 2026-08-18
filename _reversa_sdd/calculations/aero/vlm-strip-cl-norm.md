---
name: vlm-strip-cl-norm
symbol: cl_norm
kind: quantity
unit: dimensionless
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

# Normalised strip lift coefficient

**Definition.** Strip cl scaled by local chord over reference chord (AVL cl_norm convention).

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cl_norm = cl * chord / c_ref if c_ref > 0 else 0.0
```

**Inputs.**

- [[vlm-strip-cl|Local strip lift coefficient]]
- [[vlm-strip-chord|Local strip chord]]
- [[vlm-cref|Reference chord echoed to the response]]

**Produced by.** `app/services/vlm_strip_forces.py:277` — `compute_vlm_strip_forces`

**Consumed by.**

- outside it: `app/schemas/strip_forces.py:StripForceEntry.cl_norm` · `frontend/components/workbench/AnalysisViewerPanel.tsx:499`

**Source.** 🟡 PARTIAL

> AVL 3.40 source, Avl/src/aero.f:895-908 (CLTSTRP(J) = CL_LSTRP(J) * VPSQI, where VPSQI = 1/\|V_perp\|^2 and V_perp is the effective velocity with the spanwise component removed)
>
> — via `avl-advisor`

**The source states it as.**

```
AVL cl_norm = cl_strip / |V_perpendicular|^2  — the sweep/dihedral-corrected 'perpendicular cl'
```

**⚠️ Divergence from the source.** Real and significant. The code computes cl * chord / c_ref, which is the normalised SPANLOAD ordinate (c_cl / Cref), not AVL's cl_norm. The schema comment in app/schemas/strip_forces.py:20 states the app's formula as if it were the AVL convention. Since app/services/avl_strip_forces.py parses the real AVL column into the same field, StripForceEntry.cl_norm carries two incompatible quantities depending on which solver ran — they coincide only for an unswept, zero-dihedral wing at beta=0 with c = c_ref.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:277`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
