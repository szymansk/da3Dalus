---
name: alr-confidence-gate
symbol: —
kind: parameter
unit: dimensionless
cluster: aero-polars
user_visible: false
source_status: PARTIAL
---

# NeuralFoil confidence gate

**Definition.** Minimum analysis_confidence for an alpha point to enter metric extraction.

**Value.** `0.90`

**Formula — as the code writes it.**

```
confidence_gate: float = 0.90
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:415` — `compute_airfoil_low_re`

**Consumed by.**

- in this graph: [[alr-cd-min|Section CD_min]] · [[alr-cl-max|Section CL_max]] · [[alr-cl-valid-range|Polar-fit validity CL range]] · [[alr-polar-cd0|Airfoil cd0 (parabolic fit vertex)]]
- outside it: `compute_airfoil_low_re:486` · `settings.low_re_confidence_gate (app/settings.py:98)`

**Source.** 🟡 PARTIAL

> Sharpe (2024), §7.2.4 — analysis_confidence = σ(raw logit − Mahalanobis²) trained as an XFoil-convergence classifier; Fig. 7-10 reports '>0.9 for typical attached-flow operating points'
>
> — via `aerosandbox-expert`

**⚠️ Divergence from the source.** 0.90 coincides with the thesis's own description of the confident regime, so the magnitude is defensible. But the thesis prescribes no acceptance threshold, and AeroSandbox's own documented optimisation pattern constrains analysis_confidence > 0.95. The code cites nothing.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `trusted = conf_arr >= confidence_gate`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
