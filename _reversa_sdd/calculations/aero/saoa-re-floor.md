---
name: saoa-re-floor
symbol: —
kind: constant
unit: dimensionless
cluster: aero-strips
user_visible: false
source_status: PARTIAL
node_class: unclassified-constant
tags:
  - cluster/aero-strips
  - class/unclassified-constant
  - source/partial
  - flag/anomaly
  - flag/divergence
---

# Reynolds floor

**Definition.** Lower clamp on local Reynolds number to keep NeuralFoil evaluable.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `1e4`

**Formula — as the code writes it.**

```
max(velocity * chord / nu, 1e4)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/section_aoa_service.py:162` — `_compute_alpha_l0_per_section`

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🟡 PARTIAL

> Sharpe, PhD thesis (MIT, 2024) §7.2.5, NeuralFoil training data: Reynolds number log-normal, 95% of cases within [1.87e3, 2.62e8], full range [0.916, 2.92e12]
>
> — via `aerosandbox-expert`

**The source states it as.**

```
NeuralFoil is trained across ~9 decades of Re; 1e4 lies comfortably inside the well-sampled band
```

**⚠️ Divergence from the source.** The clamp is conservative rather than necessary — NeuralFoil is trained far below 1e4 and would return an answer there. No source prescribes 1e4 specifically, and it is applied silently.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Undeclared clamp: Re is silently raised to 1e4 with no warning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/section_aoa_service.py:162`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
