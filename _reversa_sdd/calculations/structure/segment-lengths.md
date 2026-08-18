---
name: segment-lengths
kind: quantity
unit: mm
cluster: structure
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/no-source-found
  - flag/anomaly
---

# Per-segment spanwise lengths

**Definition.** Spanwise length of each wing segment, read from the millimetre WingConfiguration; the basis for every span-fraction mapping and for the half-span.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
self._segment_lengths = [float(s.length) for s in wing_config.segments]
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `cad_designer/airplane/geometry/section_geometry.py:192` — `SectionGeometry.__init__`

**Consumed by.**

- in this graph: `Wing half-span` · `Host segment root spanwise position` · `Global span fraction per segment station` · `Spanwise position to segment index` · `Post-split sub-segment lengths` · `Span fraction to segment mapping`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cad_designer/airplane/geometry/section_geometry.py:234` · `cad_designer/airplane/geometry/section_geometry.py:349` · `cad_designer/airplane/geometry/section_geometry.py:415` · `cad_designer/airplane/geometry/spar_solver.py:784` · `app/services/spar_insert_service.py:89`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (reads geometry from the wing configuration; not a design calculation)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Two producers of the same list: cad_designer/airplane/geometry/section_geometry.py:192 and app/services/spar_insert_service.py:89 (_segment_lengths_mm), which rebuilds the WingConfiguration a second time to read the same numbers.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Units: millimetres throughout, wing-local frame (origin root-LE, z up).`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
