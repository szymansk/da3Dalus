---
name: w-min
symbol: w_min
kind: quantity
unit: m/s
cluster: aero-spanwise
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/partial
  - surface/user-visible
---

# Minimum sink rate

**Definition.** Lowest sink rate on the curve.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
w_min=float(w[i_min_sink])
```

**Inputs.**

- [[speed-polar-w|Sink rate]]
- [[i-min-sink|Minimum-sink index]]

**Produced by.** `app/services/analysis_service.py:544` — `_compute_speed_polar`

**Consumed by.**

- outside it: `SpeedPolarCurve.w_min` · `frontend AnalysisViewerPanel.tsx:288`

**Source.** 🟡 PARTIAL

> RC-Network Wiki 'Gleitzahl'; no explicit minimum-sink-rate source found.
>
> — via `rc-aircraft-designer`

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
