---
name: cm-gradient
kind: quantity
unit: 1/deg
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
  - flag/divergence
---

# Local Cm gradient

**Definition.** Numerical derivative of Cm with respect to alpha along the sweep.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cm_grad = np.gradient(cm_curve, alpha_cm) if len(cm_curve) > 1 else np.array([np.nan])
```

**Inputs.**

- [[cm-values|Pitching-moment coefficient array]]
- [[alpha-array|Alpha sweep array]]

**Produced by.** `app/services/analysis_service.py:1109` — `_plot_cm_stability`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Cm-gradient stability colours`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> Sadraey §11.6.2 Eq. 11.17 (C_mα as the derivative of pitching moment w.r.t. α)
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
C_mα = dC_m/dα
```

**⚠️ Divergence from the source.** np.gradient against α in degrees gives a per-degree local derivative; the source quantity is per radian. Local (point-wise) rather than the source's linear-range constant.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
