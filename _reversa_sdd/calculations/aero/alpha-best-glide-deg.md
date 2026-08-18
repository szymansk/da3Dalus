---
name: alpha-best-glide-deg
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

# Alpha at best glide

**Definition.** Angle of attack at the best-glide CL via the linear lift curve.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
alpha_best_glide_deg_val = _cl_to_alpha_deg(float(cl_s[i_best]), cl_alpha_per_rad, alpha_0_deg)
```

**Inputs.**

- [[cl-values|Lift coefficient array]]
- [[i-best-glide|Best-glide index]]
- [[cl-alpha-per-rad|Lift-curve slope from context]]
- [[alpha-0-deg|Zero-lift angle from context]]

**Produced by.** `app/services/analysis_service.py:530` — `_compute_speed_polar`

**Consumed by.**

- outside it: `SpeedPolarCurve.alpha_best_glide_deg (API only)`

**Source.** 🟢 SOURCED

> Anderson 6e §4.3 (linear lift-curve relation); Scholz §5.7 (C_L,md is well inside the linear range)
>
> — via `aerodynamics-expert, aircraft-design-scholz`

**The source states it as.**

```
C_L = C_Lα·(α − α_L=0); C_L,md = sqrt(π·A·e·C_D,0)
```

**⚠️ Divergence from the source.** Valid — C_L,md is in the linear region. Duplicated by assumption_compute_service:674 (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Unread by the frontend; duplicated by assumption_compute_service:674 alpha_md_ctx shown in SpeedChipRow.tsx:61.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
