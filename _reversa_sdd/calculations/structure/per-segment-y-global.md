---
name: per-segment-y-global
kind: quantity
unit: dimensionless (span fraction)
cluster: structure
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Global span fraction per segment station

**Definition.** Converts a within-segment sampling fraction into the whole-surface span fraction, by accumulating preceding segment lengths.

**Formula — as the code writes it.**

```
y_globals = [(acc + f * seg_len) / total if total > 0 else 0.0 for f in local_fracs]
```

**Inputs.** [[segment-lengths|Per-segment spanwise lengths]]

**Produced by.** `cad_designer/airplane/geometry/section_geometry.py:420` — `SectionGeometry.per_segment`

**Consumed by.**

- outside it: `cad_designer/airplane/geometry/section_geometry.py:421`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (span-fraction bookkeeping; not a design calculation)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
