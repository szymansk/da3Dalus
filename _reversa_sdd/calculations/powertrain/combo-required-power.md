---
name: combo-required-power
symbol: P_req
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
  - flag/divergence
---

# Power required for a motor+battery combo

**Definition.** Electrical power required to hold level flight at the target cruise speed with a given combo's total mass, delegated to the endurance service's drag-polar physics.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if speed_ms <= 0: return 0.0 ; rho = _air_density(altitude_m) ; return _power_required(rho=rho, v=speed_ms, cd0=cd0, e=e_oswald, ar=ar, mass=total_mass_kg, s_ref=s_ref_m2, eta_total=eta_total)
```

**Inputs.**

- [[air-density-sizing|Air density at altitude (sizing)]]
- [[resolved-cd0|Resolved zero-lift drag coefficient]]  — *⤵ fallback*
- [[resolved-e-oswald|Resolved Oswald efficiency]]
- [[resolved-ar|Resolved aspect ratio]]
- [[resolved-s-ref|Resolved wing reference area]]
- [[combo-total-mass|Combo total mass]]
- [[combo-eta-total|Combo total propulsive efficiency]]  — *⤵ fallback*

**Produced by.** `app/services/powertrain_sizing_service.py:92` — `_combo_required_power_w`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Estimated cruise power`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_sizing_service.py:240`

**Source.** 🟢 SOURCED

> Sadraey, M., Aircraft Design: A Systems Engineering Approach (Wiley 2013), §4.6 (Maximum Speed Sizing for Prop-Driven Aircraft), Eqs. 4.50-4.56: at level flight P_avl = P_req, eta_P P_max = T V_max with T = D; substituting D = 0.5 rho V^2 S C_D and C_L = 2W/(rho V^2 S) into the polar C_D = C_Do + K C_L^2, K = 1/(pi e AR), yields Eq. 4.55. Also §8.8.1 Eq. 8.15: eta_P = T V / P_in, stated as 'valid for all prop-driven engines - piston, turboprop, solar-powered, electric, and even human-powered'.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
eta_P P = D V, with D = 0.5 rho V^2 S (C_Do + K C_L^2), C_L = 2W/(rho V^2 S), K = 1/(pi e AR)  =>  P_req = 0.5 rho V^3 S C_D / eta_P  (Sadraey Eqs. 4.50-4.55, 8.15)
```

**⚠️ Divergence from the source.** Formula matches the source. One guard does not: the code returns 0.0 W for speed <= 0 while the delegate returns +inf. Sadraey's Eq. 4.55 diverges to infinity as V -> 0 (the induced term goes as 1/V), so +inf is the physical limit and 0.0 W inverts it.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Returns 0.0 W for speed <= 0 while the delegate returns +inf for the same input (endurance_service.py:115) — the guard inverts the physics before it is reached.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `docstring: "Delegates physics to endurance_service._power_required with per-combo aerodynamic geometry rather than hardcoded constants (gh-490 Model A)." — the delegate's own docstring (endurance_service.py:88-93): "P_req(V) = D(V) · V / η_total = (½·ρ·V²·S·C_D(V)) · V / η_total with C_D(V) = C_D0 + C_L(V)² / (π·e·AR) and C_L(V) = 2·m·g / (ρ·V²·S)"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
