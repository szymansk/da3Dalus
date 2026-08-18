---
name: ss-lift-coefficient
symbol: C_L
kind: quantity
unit: dimensionless
cluster: powertrain
user_visible: false
source_status: SOURCED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/sourced
  - flag/anomaly
  - flag/divergence
---

# Level-flight lift coefficient

**Definition.** Lift coefficient required to hold level flight at the evaluated speed.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cl = (mass_kg * g) / (q * s_ref)
```

**Inputs.**

- [[ss-dynamic-pressure|Dynamic pressure]]
- [[ss-mass|All-up mass (solution space)]]  — *⤵ fallback*
- [[ss-g-param|Gravitational acceleration (solution space input)]]
- [[ss-s-ref|Wing reference area (solution space)]]  — *⤵ fallback*

**Produced by.** `app/services/powertrain_solution_space_service.py:103` — `_p_aero`

**Consumed by.**

- in this graph: `Total drag coefficient`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:104`

**Source.** 🟢 SOURCED

> Sadraey, Aircraft Design: A Systems Engineering Approach (Wiley 2013), §4.6, Eq. 4.55 derivation: 'Substituting D = 0.5 rho V^2 S C_D and C_L = 2W/(rho V^2 S) into Equation 4.50'. RC-scale restatement in Lennon, A., Basics of R/C Model Aircraft Design (Air Age 1996), Ch. 1 & 3: CL = (Lift x 3519)/(sigma V^2 S) in model units (oz, mph, sq in).
>
> — via `aircraft-design-scholz / rc-aircraft-designer`

**The source states it as.**

```
C_L = 2 W / (rho V^2 S)  (Sadraey, in the Eq. 4.55 derivation);  C_L = Lift x 3519/(sigma V^2 S)  (Lennon Ch. 1/3, model units)
```

**⚠️ Divergence from the source.** Formula matches. Lennon Ch. 18 adds a check the code omits: level-flight C_L for a model is normally 0.2-0.3, and the nomograph is entered with that band as the MINIMUM level-flight speed, adding ~25% for climb and maneuvers. The code never bounds C_L, so a cruise speed below stall yields a finite, plausible-looking power number.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Never checked against cl_max — the model will happily report the power required at a C_L the wing cannot reach, so a v_cruise below stall produces a finite, plausible-looking power number.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `docstring: "C_L    = 2·m·g / (ρ·V²·S_ref)"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
