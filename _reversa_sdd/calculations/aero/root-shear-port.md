---
name: root-shear-port
kind: quantity
unit: N
cluster: aero-spanwise
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Port root shear

**Definition.** Peak shear at the port root.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
root_shear_N_port: float = Field(..., description="Peak shear at the port root (N)")
```

**Inputs.**

- [[spanwise-shear|Running shear force]]

**Produced by.** `app/schemas/spanwise_loads.py:60` — `SurfaceSpanwiseLoads.root_shear_N_port`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

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
