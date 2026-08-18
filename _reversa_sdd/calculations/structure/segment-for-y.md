---
name: segment-for-y
kind: quantity
unit: index
cluster: structure
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
---

# Spanwise position to segment index

**Definition.** Resolves a spanwise position (mm) to the wing segment that contains it, via accumulated segment lengths. Positions beyond the last boundary clamp to the last segment; negative (mirror) positions clamp to segment 0.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
y = abs(float(y_mm))
upper = 0.0
for idx, length in enumerate(segment_lengths_mm):
    upper += length
    if y < upper:
        return idx
return len(segment_lengths_mm) - 1
```

**Inputs.**

- [[segment-lengths|Per-segment spanwise lengths]]
- [[station-y-mm|Station spanwise position]]

**Produced by.** `app/services/spar_insert_service.py:108` — `_segment_for_y`

**Consumed by.**

- in this graph: `Host segment root spanwise position`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_insert_service.py:212` · `app/services/spar_insert_service.py:302`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (geometric index lookup; not a design calculation. The undeclared fallback — an empty segment list returning 0 — has no source basis either way)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Undeclared fallback: an empty segment list returns 0 (line 101), silently homing every spare into a segment that may not exist.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Segment ``i`` spans ``[sum(lengths[:i]), sum(lengths[:i+1]))``. A position at or beyond the last boundary clamps to the last segment; a negative (mirror) position clamps to the root segment 0.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
