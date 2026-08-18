---
name: alr-min-analysis-confidence
symbol: —
kind: quantity
unit: dimensionless
cluster: aero-polars
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Windowed min analysis confidence

**Definition.** Minimum NeuralFoil analysis_confidence over the attached-alpha window, with whole-sweep fallback.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
window_mask = (alpha_deg >= alpha_attached_lo) & (alpha_deg <= alpha_attached_hi)
window_conf = conf_arr[window_mask]
window_finite = window_conf[np.isfinite(window_conf)]
if len(window_finite) < 4:
    return fallback
return float(np.min(window_finite))
```

**Inputs.**

- [[alr-alpha-attached-window|Attached-flow alpha window]]  — *⊣ limit*

**Produced by.** `app/services/airfoil_low_re_service.py:566` — `_windowed_min_confidence`

**Consumed by.**

- in this graph: `Suitability caveat block` · `Confidence sort tier`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `AirfoilLowRePolarModel.min_analysis_confidence` · `suitability_service:534,537,551,567,625` · `frontend AirfoilSuitabilityCard.tsx:344,372`

**Source.** 🟡 PARTIAL

> Sharpe (2024), §7.2.4 — analysis_confidence is a self-reported UQ scalar in (0,1), trained as an XFoil-convergence classifier with a Mahalanobis-distance correction guaranteeing decay under extrapolation
>
> — via `aerosandbox-expert`

**⚠️ Divergence from the source.** The underlying quantity is fully sourced. Reducing it to a windowed minimum over the attached-α range is an in-repo aggregation with no source. AirfoilLowRePolarModel:104 still documents the pre-gh-825 behaviour ('min over the swept α-range').

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** AirfoilLowRePolarModel:104 still documents it as 'Trust badge: min over the swept α-range' although gh-825 changed it to the windowed minimum.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `finite_conf = conf_arr[np.isfinite(conf_arr)]
fallback = float(np.min(finite_conf)) if len(finite_conf) > 0 else 0.0`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
