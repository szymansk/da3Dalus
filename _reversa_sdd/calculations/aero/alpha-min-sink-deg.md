---
name: alpha-min-sink-deg
kind: quantity
unit: deg
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Alpha at minimum sink

**Definition.** Angle of attack at the min-sink CL via the linear lift curve.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
alpha_min_sink_deg_val = _cl_to_alpha_deg(float(cl_s[i_min_sink]), cl_alpha_per_rad, alpha_0_deg)
```

**Inputs.**

- [[cl-values|Lift coefficient array]]
- [[i-min-sink|Minimum-sink index]]
- [[cl-alpha-per-rad|Lift-curve slope from context]]
- [[alpha-0-deg|Zero-lift angle from context]]

**Produced by.** `app/services/analysis_service.py:527` — `_compute_speed_polar`

**Consumed by.**

- outside it: `SpeedPolarCurve.alpha_min_sink_deg (API only)`

**Source.** 🟢 SOURCED

> Anderson 6e §4.3 (linear lift-curve relation)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
C_L = C_Lα·(α − α_L=0)
```

**⚠️ Divergence from the source.** Valid here: the min-sink C_L normally lies inside the linear region, so the inversion is legitimate — unlike alpha-stall-deg. Duplicated by assumption_compute_service:675 (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Unread by the frontend; duplicated by assumption_compute_service:675 alpha_min_sink_ctx which is what SpeedChipRow.tsx:47 actually shows (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
