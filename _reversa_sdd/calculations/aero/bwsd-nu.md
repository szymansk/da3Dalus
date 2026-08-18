---
name: bwsd-nu
symbol: nu
kind: constant
unit: m²/s
cluster: aero-strips
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: physical-constant
tags:
  - cluster/aero-strips
  - class/physical-constant
  - source/partial
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - flag/scale
  - flag/physical
---

# Kinematic viscosity (section builder)

**Definition.** Hardcoded kinematic viscosity used for the per-section Reynolds number.

**Physical constant.** A value of nature. It must be identical everywhere it appears — a second definition is a defect by construction, not a judgement call.
*Identified as: kinematic viscosity of air.*

**Value.** `1.5e-5`

**Formula — as the code writes it.**

```
nu = 1.5e-5  # kinematic viscosity [m²/s]
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/turbulator_optimizer_service.py:396` — `build_wing_section_data`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Local section Reynolds number`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟡 PARTIAL

> ISO 2533:1975 / U.S. Standard Atmosphere 1976 (nu_0 = mu_0/rho_0 = 1.7894e-5/1.225 = 1.4607e-5 m^2/s); AeroSandbox asb.Atmosphere.kinematic_viscosity()
>
> — via `aerodynamics-expert, aerosandbox-expert`

**The source states it as.**

```
nu_0 = 1.4607e-5 m^2/s at ISA sea level
```

**⚠️ Divergence from the source.** Same +2.7% rounding as saoa-nu, and a literal duplicate of it. Two hardcoded copies of one physical constant, neither altitude-aware, alongside 1.46e-5 in suitability_service.py and the correct atm.kinematic_viscosity() in neuralfoil_cdcl_service.py.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Not a transport-category constant — ISA sea-level nu is scale-neutral. Numerical impact at RC Re is negligible (<1% on cd); the finding is the four-way inconsistency, not the value.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Duplicate of section_aoa_service.py:141 — same constant defined twice, and neither is altitude-aware unlike neuralfoil_cdcl_service.py:22 (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:396`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
