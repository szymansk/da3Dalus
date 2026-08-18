---
name: root-bm-starboard
symbol: M_root
kind: quantity
unit: N·m
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
---

# Starboard root bending moment

**Definition.** Headline spar-sizing bending moment at the starboard root.

**Formula — as the code writes it.**

```
root_bending_moment_Nm_starboard: float = Field(..., description="Root bending moment on the starboard half (N·m) — headline spar-sizing value")
```

**Inputs.** [[spanwise-bending-moment|Running bending moment]]

**Produced by.** `app/schemas/spanwise_loads.py:61` — `SurfaceSpanwiseLoads.root_bending_moment_Nm_starboard`

**Consumed by.**

- in this graph: [[sizing-half-span-selection|Design half-span selection]]
- outside it: `_surface_to_stations:2206` · `frontend AnalysisViewerPanel.tsx:932` · `frontend/lib/sparPlanHelpers.ts:59`

**Source.** 🟢 SOURCED

> Scholz 07_WingDesign §7.4 (Wing Box and Structural Spars); Sadraey §5.8; RC-Network Wiki 'Holm (Flugzeugkonstruktion)', https://wiki.rc-network.de/wiki/Holm
>
> — via `aircraft-design-scholz, rc-aircraft-designer`

**The source states it as.**

```
Structural depth increases toward the root where bending moments are largest; the spar (Holm) bears the majority of bending loads from lift; bending stiffness EI ∝ h³
```

**⚠️ Divergence from the source.** None — root bending moment as the headline spar-sizing value is exactly what all three sources prescribe.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
