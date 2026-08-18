---
name: combo-cruise-power
symbol: actual_cruise_power
kind: quantity
unit: W
cluster: powertrain
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/sourced
  - surface/user-visible
---

# Estimated cruise power

**Definition.** Electrical power this combo needs at the target cruise speed — the headline number shown per recommendation.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
actual_cruise_power = _combo_required_power_w(speed_ms=request.target_cruise_speed_ms, total_mass_kg=total_mass, altitude_m=request.altitude_m, cd0=cd0, e_oswald=e_oswald, ar=ar, s_ref_m2=s_ref_m2, eta_total=eta_total)
```

**Inputs.**

- [[combo-required-power|Power required for a motor+battery combo]]
- [[combo-total-mass|Combo total mass]]
- [[combo-eta-total|Combo total propulsive efficiency]]  — *⤵ fallback*
- [[resolved-cd0|Resolved zero-lift drag coefficient]]  — *⤵ fallback*
- [[resolved-e-oswald|Resolved Oswald efficiency]]
- [[resolved-ar|Resolved aspect ratio]]
- [[resolved-s-ref|Resolved wing reference area]]

**Produced by.** `app/services/powertrain_sizing_service.py:240` — `_evaluate_motor_battery_combo`

**Consumed by.**

- in this graph: `Cruise current draw`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_sizing_service.py:251` · `app/services/powertrain_sizing_service.py:269` · `frontend/components/workbench/PowertrainSizingModal.tsx:203`

**Source.** 🟢 SOURCED

> Sadraey (2013), §4.6, Eqs. 4.50-4.55 (power required in level flight from the drag polar) and §8.8.1 Eq. 8.15 (eta_P = T V/P_in).
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
P_req = 0.5 rho V^3 S (C_Do + K C_L^2) / eta_total,  C_L = 2 m g/(rho V^2 S),  K = 1/(pi e AR)
```

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
