---
name: ss-p-cruise-mid
symbol: p_cruise_w
kind: quantity
unit: W
cluster: powertrain
user_visible: true
source_status: SOURCED
---

# Electrical cruise power (mid band)

**Definition.** Battery-side power at cruise using the mid-band propeller efficiency; drives the energy budget.

**Formula — as the code writes it.**

```
p_cruise_mid = _p_elec(p_aero_cruise, eta_mid, assumptions.eta_motor, assumptions.eta_esc)
```

**Inputs.** [[ss-p-elec|Electrical power required]] · [[ss-p-aero-cruise|Aerodynamic power at cruise]] · [[ss-eta-mid|Mid-band propeller efficiency]] · [[ss-eta-motor|Motor efficiency (solution space)]] · [[ss-eta-esc|ESC efficiency (solution space)]]

**Produced by.** `app/services/powertrain_solution_space_service.py:360` — `compute_solution_space`

**Consumed by.**

- in this graph: [[ss-energy-wh|Required mission energy]]
- outside it: `app/services/powertrain_solution_space_service.py:377` · `app/services/powertrain_solution_space_service.py:433`

**Source.** 🟢 SOURCED

> Sadraey (2013), §8.8.1 Eq. 8.15 (eta_P = T V/P_in, valid for electric propulsion) applied to the §4.6 Eq. 4.55 cruise power.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
P_elec = P_aero / (eta_prop eta_motor eta_esc)
```

**⚠️ Anomaly.** Shipped as SolutionRow.p_cruise_w but never rendered (notes F6).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
