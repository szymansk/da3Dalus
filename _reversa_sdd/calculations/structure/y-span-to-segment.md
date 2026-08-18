---
name: y-span-to-segment
kind: quantity
unit: (index, dimensionless)
cluster: structure
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/no-source-found
  - audit/confirmed
  - flag/anomaly
---

# Span fraction to segment mapping

**Definition.** Maps a whole-surface span fraction to (segment index, relative position within that segment) by accumulating segment lengths. y_span is clamped to [0,1]; a seam resolves to the end of the lower segment.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
y = min(max(y_span, 0.0), 1.0)
total = float(sum(segment_lengths))
...
target = y * total
acc = 0.0
for idx, seg_len in enumerate(segment_lengths):
    seg_len = float(seg_len)
    if seg_len <= 0.0:
        continue
    if target <= acc + seg_len or idx == len(segment_lengths) - 1:
        rel = (target - acc) / seg_len
        return idx, min(max(rel, 0.0), 1.0)
    acc += seg_len
```

**Inputs.**

- [[segment-lengths|Per-segment spanwise lengths]]

**Produced by.** `cad_designer/airplane/geometry/section_geometry.py:117` — `_y_span_to_segment`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Section lower surface height (analytic)` · `Section upper surface height (analytic)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cad_designer/airplane/geometry/section_geometry.py:234` · `cad_designer/airplane/geometry/section_geometry.py:349`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (geometric index mapping; not a design calculation. The undeclared fallback — a zero-total-length wing silently returning (0, 0.0) — has no source basis either way)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Undeclared fallback: a zero-total-length wing silently returns (0, 0.0) — the root of the first segment — rather than signalling degenerate geometry.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** ```relative_length`` is the 0..1 position *within* that segment. ``y_span`` is clamped to ``[0, 1]``. The seam between two segments resolves to the end (``relative_length == 1.0``) of the lower segment.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
