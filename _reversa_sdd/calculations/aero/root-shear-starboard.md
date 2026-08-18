---
name: root-shear-starboard
kind: quantity
unit: N
cluster: aero-spanwise
user_visible: true
source_status: PARTIAL
---

# Starboard root shear

**Definition.** Peak shear at the starboard root.

**Formula — as the code writes it.**

```
root_shear_N_starboard: float = Field(..., description="Peak shear at the starboard root (N)")
```

**Inputs.** [[spanwise-shear|Running shear force]]

**Produced by.** `app/schemas/spanwise_loads.py:59` — `SurfaceSpanwiseLoads.root_shear_N_starboard`

**Consumed by.**

- outside it: `frontend AnalysisViewerPanel.tsx:933`

**Source.** 🟡 PARTIAL

> Scholz 07_WingDesign §7.4 (spar webs resist shear; loads maximal at the root)
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** Concept sourced, discrete value not (see spanwise-shear).

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
