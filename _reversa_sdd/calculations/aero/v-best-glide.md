---
name: v-best-glide
symbol: V_md
kind: quantity
unit: m/s
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
---

# Best-glide speed

**Definition.** Speed at maximum L/D.

**Formula — as the code writes it.**

```
v_best_glide=float(v[i_best])
```

**Inputs.** [[speed-polar-v|Glide forward speed]] · [[i-best-glide|Best-glide index]]

**Produced by.** `app/services/analysis_service.py:545` — `_compute_speed_polar`

**Consumed by.**

- outside it: `SpeedPolarCurve.v_best_glide` · `frontend AnalysisViewerPanel.tsx:292`

**Source.** 🟢 SOURCED

> RC-Network Wiki 'Gleitzahl'; Scholz 05_PreliminarySizing §5.7 (C_L,md, V_md — minimum-drag speed)
>
> — via `rc-aircraft-designer, aircraft-design-scholz`

**The source states it as.**

```
C_L,md = sqrt(π·A·e·C_D,0); best glide occurs at V_md
```

**⚠️ Divergence from the source.** Sources give V_md analytically from the parabolic polar; the code takes argmax over the discrete polar. The code's symbol V_md matches Scholz's notation.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
