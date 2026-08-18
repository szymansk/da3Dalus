---
name: fe_q
symbol: q
kind: quantity
unit: Pa
cluster: perf-envelope
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/sourced
  - audit/confirmed
---

# Dynamic pressure

**Definition.** Free-stream dynamic pressure at each sweep speed.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
q = 0.5 * rho * v**2
```

**Inputs.**

- [[fe_rho_default|Default air density (flight envelope)]]  — *⤵ fallback*
- [[fe_v_sweep|Velocity sweep points]]

**Produced by.** `app/services/flight_envelope_service.py:325` — `compute_vn_curve`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Negative maneuver load factor` · `Positive maneuver load factor`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §1.5 (definition of dynamic pressure).
>
> — via `aero`

**The source states it as.**

```
q = 0.5*rho*V^2
```

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
