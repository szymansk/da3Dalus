---
name: ss-p-aero
symbol: P_aero
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

# Aerodynamic power

**Definition.** Power the airframe absorbs aerodynamically in level flight at a given speed: drag times velocity.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if v <= 0: return float("inf") ; q = 0.5 * rho * v * v ; cl = (mass_kg * g) / (q * s_ref) ; k = 1.0 / (math.pi * e * ar) ; cd = cd0 + k * cl * cl ; return q * s_ref * cd * v
```

**Inputs.**

- [[ss-dynamic-pressure|Dynamic pressure]]
- [[ss-drag-coefficient|Total drag coefficient]]
- [[ss-s-ref|Wing reference area (solution space)]]  — *⤵ fallback*

**Produced by.** `app/services/powertrain_solution_space_service.py:105` — `_p_aero`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Aerodynamic power at cruise` · `Aerodynamic power at top speed` · `Electrical power required`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:349` · `app/services/powertrain_solution_space_service.py:350`

**Source.** 🟢 SOURCED

> Sadraey (2013), §4.6, Eqs. 4.50 and 4.55: at level flight the required power is P_req = T V = D V, with D = 0.5 rho V^2 S (C_Do + K C_L^2) and C_L = 2W/(rho V^2 S).
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
P_aero = D V = 0.5 rho V^3 S (C_Do + C_L^2/(pi e AR)),  C_L = 2 m g/(rho V^2 S)
```

**⚠️ Divergence from the source.** Formula matches Sadraey exactly. Note the code returns pure aerodynamic power while the sizing service's delegate returns power already divided by eta_total — Sadraey's Eq. 4.50 keeps the two explicitly separate (eta_P P_max = T V_max), so the solution-space contract is the one that matches the source.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Third independent producer of level-flight power required in this cluster, alongside endurance_service._power_required (used by the sizing service) and the thrust-power path in powertrain_performance. _p_aero returns pure aero power while _power_required returns aero power already divided by eta_total — same physics, different contract (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `module docstring: "All equations from the spec doc (2026-06-13-powertrain-solution-space-design.md): C_L(V) = 2·m·g / (ρ·V²·S_ref) ; C_D(V) = cd0 + C_L² / (π·e·AR) ; P_aero(V) = ½·ρ·V³·S_ref·C_D(V)"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
