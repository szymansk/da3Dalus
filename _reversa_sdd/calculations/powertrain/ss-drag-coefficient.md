---
name: ss-drag-coefficient
symbol: C_D
kind: quantity
unit: dimensionless
cluster: powertrain
user_visible: false
source_status: SOURCED
---

# Total drag coefficient

**Definition.** Parabolic drag polar: parasite plus lift-induced.

**Formula — as the code writes it.**

```
cd = cd0 + k * cl * cl
```

**Inputs.** [[ss-cd0|Zero-lift drag coefficient (solution space)]] · [[ss-induced-drag-factor|Induced-drag factor]] · [[ss-lift-coefficient|Level-flight lift coefficient]]

**Produced by.** `app/services/powertrain_solution_space_service.py:104` — `_p_aero`

**Consumed by.**

- in this graph: [[ss-p-aero|Aerodynamic power]]
- outside it: `app/services/powertrain_solution_space_service.py:105`

**Source.** 🟢 SOURCED

> Anderson, J.D., Fundamentals of Aerodynamics, 6th ed., §6.7.2 (Airplane Drag Polar and Oswald Efficiency Factor): C_D = C_D,0 + C_L^2/(pi e_tilde AR), described there as 'the cornerstone of conceptual aircraft design'. Same relation in Sadraey (2013) §4.6, Eq. 4.55 derivation.
>
> — via `aerodynamics-expert / aircraft-design-scholz`

**The source states it as.**

```
C_D = C_D,0 + C_L^2 / (pi * e_tilde * AR),  with e_tilde = 1/(1 + r pi e AR)
```

**Cited in the code itself.** `docstring: "C_D    = cd0 + C_L² / (π·e·AR)"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
