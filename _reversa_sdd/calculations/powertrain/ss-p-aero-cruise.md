---
name: ss-p-aero-cruise
symbol: p_aero_cruise_w
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
---

# Aerodynamic power at cruise

**Definition.** Airframe power demand at cruise speed, independent of any powertrain choice.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
p_aero_cruise = _p_aero(rho, v_cruise_mps, mass_kg, g, cd0, e_oswald, ar, s_ref_m2)
```

**Inputs.**

- [[ss-p-aero|Aerodynamic power]]
- [[ss-v-cruise|Cruise speed (solution space)]]
- [[ss-mass|All-up mass (solution space)]]  — *⤵ fallback*
- [[ss-cd0|Zero-lift drag coefficient (solution space)]]  — *⤵ fallback*
- [[ss-e-oswald|Oswald efficiency (solution space)]]  — *⤵ fallback*
- [[ss-ar|Aspect ratio (solution space)]]  — *⤵ fallback*
- [[ss-s-ref|Wing reference area (solution space)]]  — *⤵ fallback*
- [[ss-rho-param|Air density (solution space input)]]
- [[ss-g-param|Gravitational acceleration (solution space input)]]

**Produced by.** `app/services/powertrain_solution_space_service.py:349` — `compute_solution_space`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Required motor continuous shaft power` · `Electrical cruise power at high prop efficiency` · `Electrical cruise power at low prop efficiency` · `Electrical cruise power (mid band)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:360` · `app/services/powertrain_solution_space_service.py:363` · `app/services/powertrain_solution_space_service.py:367` · `app/services/powertrain_solution_space_service.py:422` · `app/services/powertrain_solution_space_service.py:492` · `frontend/components/workbench/PowertrainTab.tsx:1141`

**Source.** 🟢 SOURCED

> Sadraey (2013), §4.6, Eqs. 4.50 and 4.55: P_req = D V with the parabolic polar and C_L = 2W/(rho V^2 S), evaluated at cruise speed.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
P_aero(V_C) = 0.5 rho V_C^3 S (C_Do + C_L^2/(pi e AR))
```

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
