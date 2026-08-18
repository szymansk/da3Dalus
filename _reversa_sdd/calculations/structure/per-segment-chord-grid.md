---
name: per-segment-chord-grid
kind: constant
unit: dimensionless (x/c)
cluster: structure
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/structure
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
---

# Per-segment chord sampling grid

**Definition.** Chord positions sampled for each segment in the per-segment section grid.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `np.linspace(0.05, 0.95, n_chord)`

**Formula — as the code writes it.**

```
x_cs = np.linspace(0.05, 0.95, n_chord).tolist()
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `cad_designer/airplane/geometry/section_geometry.py:414` — `SectionGeometry.per_segment`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `cad_designer/airplane/geometry/section_geometry.py:421`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (chordwise sampling grid for the section-geometry endpoint; not used by the spar cluster. The 0.05/0.95 bounds are unexplained and inconsistent with the 0.05/0.6 bounds used by at_max_thickness in the same class)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Magic bounds 0.05/0.95 with no explanation, and inconsistent with the 0.05/0.6 bounds used by at_max_thickness in the same class. Not used by the spar cluster — only by the section-geometry endpoint (app/services/section_geometry_service.py).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `For each segment, sample ``n_span`` stations across that segment's own span and ``n_chord`` chord positions. ``y_span`` on each point is the global (whole-surface) span fraction.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
