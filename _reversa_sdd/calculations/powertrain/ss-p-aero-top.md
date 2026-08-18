---
name: ss-p-aero-top
symbol: p_aero_top_w
kind: quantity
unit: W
cluster: powertrain
user_visible: true
source_status: SOURCED
---

# Aerodynamic power at top speed

**Definition.** Airframe power demand at top speed — the peak-sizing case.

**Formula — as the code writes it.**

```
p_aero_top = _p_aero(rho, v_top_mps, mass_kg, g, cd0, e_oswald, ar, s_ref_m2)
```

**Inputs.** [[ss-p-aero|Aerodynamic power]] · [[ss-v-top|Top speed used for peak sizing]] · [[ss-mass|All-up mass (solution space)]] · [[ss-cd0|Zero-lift drag coefficient (solution space)]] · [[ss-e-oswald|Oswald efficiency (solution space)]] · [[ss-ar|Aspect ratio (solution space)]] · [[ss-s-ref|Wing reference area (solution space)]] · [[ss-rho-param|Air density (solution space input)]] · [[ss-g-param|Gravitational acceleration (solution space input)]]

**Produced by.** `app/services/powertrain_solution_space_service.py:350` — `compute_solution_space`

**Consumed by.**

- in this graph: [[ss-motor-peak-shaft|Required motor peak shaft power]] · [[ss-p-top-hi-e|Electrical peak power at high prop efficiency]] · [[ss-p-top-lo-e|Electrical peak power at low prop efficiency]] · [[ss-p-top-mid|Electrical peak power (mid band)]]
- outside it: `app/services/powertrain_solution_space_service.py:361` · `app/services/powertrain_solution_space_service.py:369` · `app/services/powertrain_solution_space_service.py:372` · `app/services/powertrain_solution_space_service.py:421` · `app/services/powertrain_solution_space_service.py:493` · `frontend/components/workbench/PowertrainTab.tsx:1052` · `frontend/components/workbench/PowertrainTab.tsx:1142`

**Source.** 🟢 SOURCED

> Sadraey (2013), §4.6, Eqs. 4.50-4.56 — the same level-flight power relation evaluated at V_max, which is precisely the peak-power sizing case Eq. 4.56 addresses.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
P_aero(V_max) = 0.5 rho V_max^3 S (C_Do + C_L^2/(pi e AR))
```

**⚠️ Scale (ADR 0023).** The V_top at which this is evaluated derives from the transport-based 1.2-1.3 heuristic (applied here as 1.4) — see ss-v-top-factor.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
