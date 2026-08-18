---
name: ss-induced-drag-factor
symbol: k
kind: quantity
unit: dimensionless
cluster: powertrain
user_visible: false
source_status: SOURCED
---

# Induced-drag factor

**Definition.** Lift-dependent drag factor of the parabolic polar.

**Formula — as the code writes it.**

```
k = 1.0 / (math.pi * e * ar)
```

**Inputs.** [[ss-e-oswald|Oswald efficiency (solution space)]] · [[ss-ar|Aspect ratio (solution space)]]

**Produced by.** `app/services/powertrain_solution_space_service.py:104` — `_p_aero`

**Consumed by.**

- in this graph: [[ss-drag-coefficient|Total drag coefficient]]
- outside it: `app/services/powertrain_solution_space_service.py:104`

**Source.** 🟢 SOURCED

> Sadraey (2013), §4.6: 'The aircraft drag polar is C_D = C_Do + K C_L^2 with K = 1/(pi e AR)' (stated in the Eq. 4.55 derivation; worked with AR ~ 12, e ~ 0.85 giving K ~ 0.031). Anderson, Fundamentals of Aerodynamics 6e, §6.7.2 gives the same induced term C_L^2/(pi e AR).
>
> — via `aircraft-design-scholz / aerodynamics-expert`

**The source states it as.**

```
K = 1 / (pi * e * AR)
```

**Cited in the code itself.** `docstring: "C_D    = cd0 + C_L² / (π·e·AR)"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
