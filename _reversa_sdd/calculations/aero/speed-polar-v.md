---
name: speed-polar-v
symbol: V
kind: quantity
unit: m/s
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/divergence
---

# Glide forward speed

**Definition.** Speed required to fly each positive-CL point in steady glide.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
v = np.sqrt(2.0 * weight_n / (rho * s_ref_m2 * cl_pos))
```

**Inputs.**

- [[weight-n|Weight]]
- [[rho-speed-polar|Air density (speed polar)]]
- [[s-ref-speed-polar|Reference wing area]]
- [[cl-values|Lift coefficient array]]

**Produced by.** `app/services/analysis_service.py:514` — `_compute_speed_polar`

**Consumed by.**

- in this graph: `Sink rate` · `Speed-polar X-axis upper bound` · `Best-glide speed` · `Minimum-sink speed`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `SpeedPolarCurve.V` · `frontend AnalysisViewerPanel speed-polar chart`

**Source.** 🟢 SOURCED

> Sadraey §4.3.2 Eq. 4.30 (Wiley 2013)
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
L = W = ½·rho·V²·S·C_L   (4.30)   ⇒   V = sqrt(2W/(rho·S·C_L))
```

**⚠️ Divergence from the source.** Sadraey writes Eq. 4.30 at C_L,max to get V_s; the code applies the identical rearrangement at every positive-CL point. Same equation. Strictly, steady glide has L = W·cos(γ), so V is over-estimated by 1/sqrt(cos γ) — under 1% for L/D > 5.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
