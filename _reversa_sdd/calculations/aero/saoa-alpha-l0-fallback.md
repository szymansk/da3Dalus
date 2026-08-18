---
name: saoa-alpha-l0-fallback
symbol: alpha_l0
kind: constant
unit: deg
cluster: aero-strips
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: numerical-tolerance
tags:
  - cluster/aero-strips
  - class/numerical-tolerance
  - source/no-source-found
  - flag/anomaly
  - flag/divergence
  - flag/scale
  - solver-adjacent/neuralfoil
---

# Zero-lift angle fallback

**Definition.** alpha_L0 defaults to 0° when NeuralFoil is unavailable or fails.

**Numerical tolerance.** A solver or comparison epsilon, not a domain value. ADR 0023 does not apply.

**Value.** `0.0`

**Formula — as the code writes it.**

```
alpha_l0 = 0.0  # NeuralFoil unavailable or failed
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/section_aoa_service.py:190` — `_compute_alpha_l0_per_section`

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🔴 NO SOURCE FOUND

> Anderson, Fundamentals of Aerodynamics 6e, §4.7 (alpha_L=0 = 0 holds ONLY for a symmetric airfoil)
>
> — via `aerodynamics-expert`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Substituting 0 deg asserts a symmetric section. For a typical cambered RC section alpha_L0 is -2 to -5 deg, so alpha_effective_deg is biased by that full amount — a several-degree error presented with no marker.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Cambered sections dominate this aircraft class, so the fallback is wrong for the typical case rather than the rare one.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Undeclared fallback: a cambered section silently gets alpha_L0 = 0°, biasing alpha_effective_deg by several degrees, with no DesignWarning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/section_aoa_service.py:176,190`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
