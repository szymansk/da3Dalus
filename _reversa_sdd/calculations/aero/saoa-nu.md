---
name: saoa-nu
symbol: nu
kind: constant
unit: m²/s
cluster: aero-strips
user_visible: false
source_status: PARTIAL
node_class: physical-constant
tags:
  - cluster/aero-strips
  - class/physical-constant
  - source/partial
  - flag/anomaly
  - flag/divergence
  - flag/scale
  - flag/physical
---

# Kinematic viscosity (section AoA)

**Definition.** Hardcoded sea-level kinematic viscosity used for the local chord Reynolds number.

**Physical constant.** A value of nature. It must be identical everywhere it appears — a second definition is a defect by construction, not a judgement call.
*Identified as: kinematic viscosity of air.*

**Value.** `1.5e-5`

**Formula — as the code writes it.**

```
nu = 1.5e-5  # kinematic viscosity [m²/s] — standard sea-level air
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/section_aoa_service.py:141` — `_compute_alpha_l0_per_section`

**Consumed by.**

- in this graph: `Local chord Reynolds number (alpha_L0 lookup)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟡 PARTIAL

> ISO 2533:1975 / U.S. Standard Atmosphere 1976, sea level: rho_0 = 1.225 kg/m^3, mu_0 = 1.7894e-5 Pa*s; AeroSandbox docs (asb.Atmosphere.kinematic_viscosity(), Sutherland law over the 1976 COESA standard)
>
> — via `aerodynamics-expert, aerosandbox-expert`

**The source states it as.**

```
nu_0 = mu_0 / rho_0 = 1.7894e-5 / 1.225 = 1.4607e-5 m^2/s
```

**⚠️ Divergence from the source.** 1.5e-5 is +2.7% against the standard value, so every Re from this path is 2.7% LOW. More important: it is altitude-blind, whereas asb.Atmosphere.kinematic_viscosity() is already available and used elsewhere in the same repo (neuralfoil_cdcl_service.py:22).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Not a transport-category import — the error is a rounding, not a scale mismatch. At RC Re ~1e5 a 2.7% Re shift moves section cd by well under 1%, far inside NeuralFoil's own ~4-8% CD error, so the numerical impact is negligible; the defect is that three different nu values coexist in one codebase.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Three competing values of nu exist in the repo: 1.5e-5 here and in turbulator_optimizer_service.py:396, 1.46e-5 in suitability_service.py:377, and the altitude-correct atm.kinematic_viscosity() in neuralfoil_cdcl_service.py:22 (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/section_aoa_service.py:141`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
