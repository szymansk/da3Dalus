---
name: v-min-sink
symbol: V_min_sink
kind: quantity
unit: m/s
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

# Minimum-sink speed

**Definition.** Speed at which the sink rate is lowest.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
v_min_sink=float(v[i_min_sink])
```

**Inputs.**

- [[speed-polar-v|Glide forward speed]]
- [[i-min-sink|Minimum-sink index]]

**Produced by.** `app/services/analysis_service.py:543` — `_compute_speed_polar`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `SpeedPolarCurve.v_min_sink` · `frontend AnalysisViewerPanel.tsx:287`

**Source.** 🟡 PARTIAL

> RC-Network Wiki 'Gleitzahl' (speed-dependent glide polar); no explicit minimum-sink-speed definition found in the consulted vaults.
>
> — via `rc-aircraft-designer`

**⚠️ Divergence from the source.** Second producer: assumption_compute_service also emits v_min_sink_mps, which is what SpeedChipRow renders (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Second producer: assumption_compute_service context also carries v_min_sink_mps (shown in SpeedChipRow) — ADR 0022.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
