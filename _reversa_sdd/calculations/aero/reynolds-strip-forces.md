---
name: reynolds-strip-forces
symbol: Re
kind: quantity
unit: -
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
  - flag/scale
  - solver-adjacent/aerobuildup
---

# Chord Reynolds number (strip-forces echo)

**Definition.** Chord-based Reynolds number echoed with the strip-forces response.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
nu = float(asb.Atmosphere(altitude=altitude).kinematic_viscosity()); return float(velocity * cref / nu)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:1731` — `_reynolds_from_atmosphere`

**Consumed by.**

- outside it: `StripForcesResponse.reynolds` · `frontend/components/workbench/AnalysisViewerPanel.tsx:589`

**Source.** 🟢 SOURCED

> Anderson 6e §1.7 ('Reynolds Number: Inertia Forces to Viscous Forces Ratio'); AeroSandbox asb.Atmosphere (U.S. 1976 COESA, Sutherland dynamic viscosity)
>
> — via `aerodynamics-expert, aerosandbox-expert`

**The source states it as.**

```
Re = rho·V·c/mu = V·c/nu; 'the characteristic length varies by application: for airfoils, it is the chord'
```

**⚠️ Divergence from the source.** Exact match to Anderson §1.7 in kinematic form. Second producer of a user-visible Re: assumption_compute_service._reynolds_number uses hardcoded rho=1.225 / mu=1.81e-5 and the MAC — the two will disagree at any non-zero altitude (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Anderson §1.7's own example band is 'aircraft wing Re ≈ 10^7'. RC/UAV chord Reynolds numbers are 5e4–5e5 — the low-Re regime where c_l,max is strongly Re-dependent (Anderson §4.3). Re here is an echo only, so no numeric defect, but consumers must not assume high-Re airfoil data.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Second producer of a user-visible Reynolds number: assumption_compute_service._reynolds_number (line 1749) uses hardcoded rho=1.225, mu=1.81e-5 and the MAC, and its value is shown in PolarChipRow.tsx:177 (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
