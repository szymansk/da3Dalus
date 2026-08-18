---
name: tos-confidence-threshold
symbol: _CONFIDENCE_THRESHOLD
kind: constant
unit: dimensionless
cluster: aero-strips
user_visible: true
source_status: PARTIAL
node_class: unclassified-constant
tags:
  - cluster/aero-strips
  - class/unclassified-constant
  - source/partial
  - surface/user-visible
  - flag/divergence
  - flag/scale
---

# NeuralFoil confidence threshold

**Definition.** Mean NeuralFoil analysis_confidence below which a warning is emitted.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.80`

**Formula — as the code writes it.**

```
_CONFIDENCE_THRESHOLD = 0.80
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/turbulator_optimizer_service.py:56` — `_CONFIDENCE_THRESHOLD`

**Consumed by.**

- outside it: `app/services/turbulator_optimizer_service.py:optimize_section_xtr` · `frontend/components/workbench/TurbulatorEditDialog.tsx (warnings list)`

**Source.** 🟡 PARTIAL

> Sharpe, PhD thesis (MIT, 2024) §7.2.4 (analysis_confidence in (0,1); worked optimisation example constrains analysis_confidence > 0.95)
>
> — via `aerosandbox-expert`

**The source states it as.**

```
opti.subject_to(sol['analysis_confidence'] > 0.95)
```

**⚠️ Divergence from the source.** The metric is sourced; 0.80 is not. The only threshold the thesis demonstrates is 0.95, so the code is materially more permissive than its own source's example and will stay silent in a band (0.80-0.95) the thesis treats as untrustworthy.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** This matters most exactly at this app's scale. The thesis (Fig. 7-10) shows confidence collapsing near C_L ~ 1.0 at Re_c ~ 80e3 — the laminar-separation-bubble regime — which is squarely the RC/UAV operating point. A threshold set below the documented one suppresses the warning precisely where the model is known to be weakest.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:56`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
