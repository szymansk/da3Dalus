---
name: root-shear-port
kind: quantity
unit: N
cluster: aero-spanwise
user_visible: true
source_status: PARTIAL
---

# Port root shear

**Definition.** Peak shear at the port root.

**Formula — as the code writes it.**

```
root_shear_N_port: float = Field(..., description="Peak shear at the port root (N)")
```

**Inputs.** [[spanwise-shear|Running shear force]]

**Produced by.** `app/schemas/spanwise_loads.py:60` — `SurfaceSpanwiseLoads.root_shear_N_port`

**Consumed by.**

- outside it: `frontend/hooks/useSpanwiseLoads.ts:24`

**Source.** 🟡 PARTIAL

> Scholz 07_WingDesign §7.4
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** Same as starboard; additionally typed in the frontend but never rendered.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Declared in the frontend interface but never rendered — AnalysisViewerPanel reads only the starboard root values.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
