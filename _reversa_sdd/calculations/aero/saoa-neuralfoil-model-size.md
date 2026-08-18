---
name: saoa-neuralfoil-model-size
symbol: model_size
kind: parameter
unit: n/a
cluster: aero-strips
user_visible: false
source_status: PARTIAL
node_class: unclassified-parameter
tags:
  - cluster/aero-strips
  - class/unclassified-parameter
  - source/partial
  - flag/divergence
---

# NeuralFoil model size (alpha_L0)

**Definition.** NeuralFoil network size used for the zero-lift-angle polar.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `"small"`

**Formula — as the code writes it.**

```
model_size="small",
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/section_aoa_service.py:183` — `_compute_alpha_l0_per_section`

**Consumed by.**

- in this graph: `Section zero-lift angle`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟡 PARTIAL

> Sharpe, PhD thesis (MIT, 2024) §7.2, model performance table: xxsmall CL MAE 0.041 / CD rel. err. 7.9% / 4 ms; medium 0.020 / 3.9% / 6 ms; xlarge 0.014 / 2.5%; xxxlarge 0.011 / 2.0%
>
> — via `aerosandbox-expert`

**The source states it as.**

```
Eight model sizes, xxsmall (1x48) to xxxlarge (5x512), trading accuracy against runtime
```

**⚠️ Divergence from the source.** 'small' is a documented option but the thesis does not tabulate it; by interpolation it lands near CL MAE ~0.03 and CD rel. err. ~5-7%. No source prescribes 'small' for this use, and the per-case runtime spread between xxsmall and xlarge is only 4 ms to 11 ms, so the accuracy is being traded for very little.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/section_aoa_service.py:183`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
