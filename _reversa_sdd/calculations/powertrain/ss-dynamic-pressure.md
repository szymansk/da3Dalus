---
name: ss-dynamic-pressure
symbol: q
kind: quantity
unit: Pa
cluster: powertrain
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/sourced
  - audit/confirmed
---

# Dynamic pressure

**Definition.** Dynamic pressure at the evaluated flight speed.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
q = 0.5 * rho * v * v
```

**Inputs.**

- [[ss-rho-param|Air density (solution space input)]]

**Produced by.** `app/services/powertrain_solution_space_service.py:102` — `_p_aero`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Level-flight lift coefficient` · `Aerodynamic power`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:103` · `app/services/powertrain_solution_space_service.py:105`

**Source.** 🟢 SOURCED

> Sadraey (2013), §4.6, Eq. 4.55 (D = 0.5 rho V^2 S C_D substituted into the level-flight power balance); Anderson, Fundamentals of Aerodynamics 6e, §1.5 defines q_inf = 0.5 rho V^2 as the dynamic pressure underlying all force coefficients.
>
> — via `aircraft-design-scholz / aerodynamics-expert`

**The source states it as.**

```
q = 0.5 rho V^2
```

**Cited in the code itself.** `docstring: "P_aero = ½·ρ·V³·S_ref·C_D"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
