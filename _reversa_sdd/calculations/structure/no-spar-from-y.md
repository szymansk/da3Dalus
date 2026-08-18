---
name: no-spar-from-y
kind: quantity
unit: mm (m in the API)
cluster: structure
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/no-source-found
  - surface/user-visible
---

# No-spar region start

**Definition.** Spanwise magnitude (starboard half) where the tip-most no-spar region begins — outboard of it the load is negligible and the D-box skin plus ribs carry the tip. None means the spar runs to the tip; the root y means the whole span is negligible.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
tip_y = max(abs(s.y_mm) for s in stations)
if not pieces:
    return min(abs(s.y_mm) for s in stations)  # whole span negligible
last = pieces[-1]
last_tip_y = abs(last.spare_origin[1] + last.length * last.spare_vector[1])
if last_tip_y < tip_y - _FIT_TOL_MM:
    return last_tip_y
return None
```

**Inputs.**

- [[piece-length|Spar piece length]]
- [[piece-direction-vector|Spar piece direction unit vector]]
- [[negligible-od-floor-mm|Buildable-minimum spar outer diameter]]  — *⊣ limit*
- [[fit-tol-mm|Containment fit tolerance]]  — *ε tolerance*

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:488` — `_no_spar_from_y`

**Consumed by.**

- outside it: `cad_designer/airplane/geometry/spar_solver.py:675` · `cad_designer/airplane/geometry/spar_solver.py:691` · `app/services/spar_plan_service.py:650` · `app/services/spar_plan_service.py:653` · `app/schemas/spar_plan.py:304` · `app/schemas/spar_plan.py:314` · `frontend/hooks/useSparPlan.ts:77` · `frontend/components/workbench/SparSizingPanel.tsx:270` · `frontend/components/workbench/SparSizingPanel.tsx:274`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer. No source read supports terminating a spar short of the tip on a strength threshold. RC-Network Wiki "Holm" describes the spar as running the wing structure with ribs threaded onto it; Kirch's procedure tapers the section outboard but never ends it. The code's own justification ("the D-box skin + ribs carry the tip") is contradicted by the project's settled record (BR-W16, gh-1079): neither manufacturing route builds a D-box, and a film covering cannot form a torsion box — that discrepancy is tracked as gh-1136.`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**Cited in the code itself.** `gh-1076 Option A. When trailing negligible-load stations produced no buildable piece, the region from the last real piece's tip to the wing tip carries no spar. ... ``y_mm`` is signed by half (port negative); the plan is symmetric, so we report the starboard-half magnitude.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
