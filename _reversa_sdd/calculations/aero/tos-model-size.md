---
name: tos-model-size
symbol: model_size
kind: parameter
unit: n/a
cluster: aero-strips
user_visible: false
source_status: PARTIAL
---

# NeuralFoil model size (optimiser)

**Definition.** NeuralFoil network size used for every optimiser polar call.

**Value.** `"small"`

**Formula — as the code writes it.**

```
model_size: str = "small"
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/turbulator_optimizer_service.py:126` — `_cd_at_cl_xtr`

**Consumed by.**

- in this graph: [[tos-cd-at-cl|Section cd at a target CL and trip position]]

**Source.** 🟡 PARTIAL

> Sharpe, PhD thesis (MIT, 2024) §7.2, model performance table (xxsmall: CD rel. err. 7.9%; medium: 3.9%; xlarge: 2.5%)
>
> — via `aerosandbox-expert`

**The source states it as.**

```
Eight sizes trading CD relative error against runtime
```

**⚠️ Divergence from the source.** 'small' is undocumented in the thesis table; by interpolation ~5-7% CD relative error.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** The optimiser's payload is delta_cd = cd_tripped - cd_clean. At RC Re, section cd is ~0.012-0.030, so a 5-7% model error is ~0.001-0.002 — the same order as the turbulator effect being resolved. The two evaluations use the SAME network at the SAME (cl, Re) and differ only in xtr, so errors are strongly correlated and largely cancel in the difference; but nothing in the code or the source quantifies that cancellation, so the absolute cd_clean / cd_tripped / L-over-D numbers shown to the user carry the full error while only the delta is defensible.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:126,219`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
