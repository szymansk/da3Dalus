---
name: trim-point-cm-zero
kind: quantity
unit: mixed (deg, -, -)
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
---

# Trim point (Cm = 0)

**Definition.** Alpha/CL/CD interpolated at the first Cm sign change.

**Formula — as the code writes it.**

```
t = 0.0 if abs(cm1 - cm0) <= 1e-12 else -cm0 / (cm1 - cm0); alpha_deg = alpha[i] + t * (alpha[i+1] - alpha[i]); CL = cl[i] + t * (cl[i+1] - cl[i]); CD = cd_values[i] + t * (cd_values[i+1] - cd_values[i])
```

**Inputs.** [[cm-values|Pitching-moment coefficient array]] · [[cl-values|Lift coefficient array]] · [[cd-values|Drag coefficient array]] · [[alpha-array|Alpha sweep array]]

**Produced by.** `app/services/analysis_service.py:198` — `_compute_trim_point`

**Consumed by.**

- in this graph: [[characteristic-points|Characteristic points dict]]
- outside it: `alpha-sweep PNG (3 panels)` · `_render_summary_panel` · `API alpha_sweep response`

**Source.** 🟢 SOURCED

> Sadraey §11.6.2 Eq. 11.17 (C_mα relation); Sadraey Ch. 12 longitudinal-trim requirement ('the airplane must maintain longitudinal trim … in level flight at all speeds')
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
trim ⇔ ΣM_cg = 0 ⇔ C_m = 0
```

**⚠️ Divergence from the source.** Source treats trim as an equilibrium to be ACHIEVED (by elevator/incidence). The code reports the α where the untrimmed Cm(α) curve happens to cross zero — valid as a diagnostic, but it is a free-stick crossing, not a trimmed flight condition.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
