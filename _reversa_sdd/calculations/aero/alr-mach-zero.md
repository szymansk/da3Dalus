---
name: alr-mach-zero
symbol: M
kind: constant
unit: dimensionless
cluster: aero-polars
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: numerical-tolerance
tags:
  - cluster/aero-polars
  - class/numerical-tolerance
  - source/sourced
  - audit/confirmed
  - flag/divergence
  - solver-adjacent/neuralfoil
---

# Mach number for NeuralFoil calls

**Definition.** Incompressible assumption forced on every low-Re polar evaluation.

**Numerical tolerance.** A solver or comparison epsilon, not a domain value. ADR 0023 does not apply.

**Value.** `0.0`

**Formula — as the code writes it.**

```
mach=0.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:472` — `compute_airfoil_low_re`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `NeuralFoil`

**Source.** 🟢 SOURCED

> Sharpe (2024), §7.2 and §7.2.5 — Mach is not in NeuralFoil's latent space; the network is trained at M = 0 and compressibility is applied analytically post-solve via Laitone's rule
>
> — via `aerosandbox-expert`

**The source states it as.**

```
training Mach = 0; M applied by Laitone correction downstream
```

**⚠️ Divergence from the source.** Passing mach=0.0 requests exactly the incompressible network output. Physically appropriate here: at RC/UAV speeds (V ≤ ~40 m/s, M ≤ 0.12) the Prandtl-Glauert/Laitone correction on CL is under ~1%.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `mach=0.0,`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
