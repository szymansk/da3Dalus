---
name: alr-model-size-default
symbol: —
kind: parameter
unit: enum
cluster: aero-polars
user_visible: false
source_status: SOURCED
node_class: unclassified-parameter
tags:
  - cluster/aero-polars
  - class/unclassified-parameter
  - source/sourced
  - flag/anomaly
  - flag/divergence
  - solver-adjacent/neuralfoil
---

# NeuralFoil model size (backfill default)

**Definition.** Surrogate network size used for the precomputed low-Re polars.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `"xxxlarge"`

**Formula — as the code writes it.**

```
model_size: str = "xxxlarge"
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:413` — `compute_airfoil_low_re`

**Consumed by.**

- outside it: `airfoil.get_aero_from_neuralfoil:474` · `AirfoilLowRePolarModel.neuralfoil_model_size`

**Source.** 🟢 SOURCED

> Sharpe (2024), §7.2, model-size performance table: xxsmall C_D rel. err. 7.9%, medium 3.9%, xlarge 2.5%, xxxlarge 2.0% (runtime 4/6/11/61 ms per case)
>
> — via `aerosandbox-expert`

**The source states it as.**

```
xxxlarge: C_D rel. err. 2.0%, C_L MAE 0.011
```

**⚠️ Divergence from the source.** 'xxxlarge ≈ 2%' is exactly right. But settings.py:90-93 states '~8% for large' — 7.9% is the figure for **xxsmall**; 'large' sits between medium (3.9%) and xlarge (2.5%), i.e. ≈3%. The accuracy penalty ascribed to the interactive endpoint is overstated by roughly 2.5×, which weakens the stated reason for keeping the two defaults apart.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Two producers of the same class of number by design: settings.py:90-93 documents 'CD error ~2% vs ~8% for large' — the interactive endpoint and the stored polars come from different-accuracy models.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Default 'xxxlarge' for the backfill;
the interactive endpoint at endpoints/airfoils.py:111 uses 'large'.
These defaults are intentionally different — do NOT collapse.`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
