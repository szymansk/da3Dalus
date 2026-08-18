---
name: ss-p-top-mid
symbol: p_top_w
kind: quantity
unit: W
cluster: powertrain
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/scale
---

# Electrical peak power (mid band)

**Definition.** Battery-side power at top speed using the mid-band propeller efficiency; drives the mid-band peak current.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
p_top_mid = _p_elec(p_aero_top, eta_mid, assumptions.eta_motor, assumptions.eta_esc)
```

**Inputs.**

- [[ss-p-elec|Electrical power required]]
- [[ss-p-aero-top|Aerodynamic power at top speed]]
- [[ss-eta-mid|Mid-band propeller efficiency]]
- [[ss-eta-motor|Motor efficiency (solution space)]]
- [[ss-eta-esc|ESC efficiency (solution space)]]

**Produced by.** `app/services/powertrain_solution_space_service.py:361` — `compute_solution_space`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/powertrain_solution_space_service.py:387` · `app/services/powertrain_solution_space_service.py:434`

**Source.** 🟢 SOURCED

> Sadraey (2013), §8.8.1 Eq. 8.15 applied to the §4.6 Eq. 4.55 power at V_max.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
P_elec(V_top) = P_aero(V_top) / (eta_prop eta_motor eta_esc)
```

**⚠️ Scale (ADR 0023).** Inherits the transport-derived V_top ratio — see ss-v-top-factor.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Shipped as SolutionRow.p_top_w but never rendered (notes F6).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
