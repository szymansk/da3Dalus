---
name: dcm-dalpha-slope
symbol: dCm/dα
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
  - flag/anomaly
  - flag/divergence
---

# Longitudinal stability slope

**Definition.** Linear-regression slope of Cm over alpha used to label the aircraft stable/neutral/unstable.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
slope = np.polyfit(x[mask], y[mask], 1)[0]
```

**Inputs.**

- [[cm-values|Pitching-moment coefficient array]]
- [[alpha-array|Alpha sweep array]]

**Produced by.** `app/services/analysis_service.py:826` — `_classify_longitudinal_stability`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `_render_summary_panel (alpha-sweep PNG)`

**Source.** 🟢 SOURCED

> Sadraey §11.6.2 Eq. 11.17 (Wiley 2013); Anderson 6e §4.x (aerodynamic centre, dc_m/dα)
>
> — via `aircraft-design-scholz, aerodynamics-expert`

**The source states it as.**

```
C_mα = C_Lα·(X_cg − X_np)   (11.17);  static stability requires C_mα < 0
```

**⚠️ Divergence from the source.** Two departures: (a) the source's C_mα is a per-RADIAN derivative in the LINEAR α range; the code polyfits over the WHOLE sweep including post-stall points, contaminating the slope; (b) the fit is against α in DEGREES so the number is per-degree while the label prints only 'dCm/da'. A per-rad reader mis-reads the value by 57×.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Fitted against alpha in degrees, so the slope is per degree while the label prints only 'dCm/da' — unit-ambiguous to the reader.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
