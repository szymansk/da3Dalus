---
name: tos-conf-mean
symbol: conf_mean
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: true
source_status: PARTIAL
---

# Mean NeuralFoil analysis confidence

**Definition.** NaN-safe mean of NeuralFoil's per-alpha analysis_confidence at the probe trip position.

**Formula — as the code writes it.**

```
conf_mean = float(np.nanmean(conf_arr))
```

**Inputs.** [[tos-confidence-probe-xtr|Confidence-probe trip position]] · [[tos-alpha-grid|Alpha grid for cd lookup]]

**Produced by.** `app/services/turbulator_optimizer_service.py:222` — `optimize_section_xtr`

**Consumed by.**

- outside it: `SectionOptimizerResult.warnings` · `frontend/components/workbench/TurbulatorEditDialog.tsx:342-348`

**Source.** 🟡 PARTIAL

> Sharpe, PhD thesis (MIT, 2024) §7.2.4 (analysis confidence as a per-query scalar, used pointwise as an optimisation constraint or an active-learning acquisition signal)
>
> — via `aerosandbox-expert`

**The source states it as.**

```
Analysis Confidence = sigmoid(raw logit - Mahalanobis^2 of the query from the training distribution)
```

**⚠️ Divergence from the source.** The thesis uses the value POINTWISE. Averaging it over an alpha grid is not a documented use and it is precisely the wrong reduction: a mean hides a narrow low-confidence band. The default of [1.0] when the key is absent additionally makes a NeuralFoil build without the output look perfectly confident.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** The thesis's worked example of a confidence collapse is C_L ~ 1.0 at Re_c ~ 80e3 (laminar separation bubble) — the RC/UAV design point. A mean over -4..+14 deg will average that collapse away.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Default confidence is [1.0] when the key is missing (line 221), so a NeuralFoil build without analysis_confidence always looks fully confident.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:221-227`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
