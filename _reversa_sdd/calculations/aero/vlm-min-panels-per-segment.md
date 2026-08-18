---
name: vlm-min-panels-per-segment
symbol: _MIN_PANELS_PER_SEGMENT
kind: constant
unit: panels
cluster: aero-strips
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Minimum panels per wing segment

**Definition.** Floor on spanwise panels allotted to any single wing segment.

**Value.** `2`

**Formula — as the code writes it.**

```
_MIN_PANELS_PER_SEGMENT = 2
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/vlm_strip_forces.py:60` — `_MIN_PANELS_PER_SEGMENT`

**Consumed by.**

- in this graph: [[vlm-panels-per-segment|Panels allotted to a wing segment]] · [[vlm-panels-per-segment-degenerate|Degenerate-span panel fallback]]
- outside it: `app/services/vlm_strip_forces.py:_remesh_airplane` · `app/services/vlm_strip_forces.py:compute_vlm_strip_forces`

**Source.** 🔴 NO SOURCE FOUND

> AVL 3.40 User Primer, avl_doc.txt L1097-1108 (vortex-spacing Rule 2)
>
> — via `avl-advisor`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Rule 2 requires smooth spanwise strip width with bunching at dihedral/chord/flap breaks and wingtips. A flat floor of 2 panels on a short segment produces exactly the sudden strip-width change Rule 2 forbids. The value 2 itself is unattributable.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:60`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
