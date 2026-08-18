---
name: ld-max
symbol: (L/D)max
kind: quantity
unit: -
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Maximum lift-to-drag ratio

**Definition.** Peak glide ratio of the curve.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
ld_max=float(ld[i_best])
```

**Inputs.**

- [[speed-polar-ld|Glide ratio per point]]
- [[i-best-glide|Best-glide index]]

**Produced by.** `app/services/analysis_service.py:546` — `_compute_speed_polar`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `SpeedPolarCurve.ld_max` · `frontend AnalysisViewerPanel.tsx:292` · `frontend PolarChipRow.tsx:137 (via context)`

**Source.** 🟢 SOURCED

> Anderson 6e §6.7.2; Scholz 05_PreliminarySizing §5.7 Eq. 5.39
>
> — via `aerodynamics-expert, aircraft-design-scholz`

**The source states it as.**

```
E_max = (1/(2·C_D,0))·sqrt(π·A·e·C_D,0) = 0.5·sqrt(π·A·e/C_D,0)   (5.39)
```

**⚠️ Divergence from the source.** Discrete argmax vs analytic optimum. Third producer reaching the UI (also lines 111 and 1154 plus the computation context) — ADR 0022.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Third producer of (L/D)max reaching the UI: also max-ld-point (line 111) and the computation context's cleanPolar.ld_max — ADR 0022.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
