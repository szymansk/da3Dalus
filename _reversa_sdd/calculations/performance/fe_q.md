---
name: fe_q
symbol: q
kind: quantity
unit: Pa
cluster: perf-envelope
user_visible: false
source_status: SOURCED
---

# Dynamic pressure

**Definition.** Free-stream dynamic pressure at each sweep speed.

**Formula — as the code writes it.**

```
q = 0.5 * rho * v**2
```

**Inputs.** [[fe_rho_default|Default air density (flight envelope)]] · [[fe_v_sweep|Velocity sweep points]]

**Produced by.** `app/services/flight_envelope_service.py:325` — `compute_vn_curve`

**Consumed by.**

- in this graph: [[fe_n_neg_maneuver|Negative maneuver load factor]] · [[fe_n_pos_maneuver|Positive maneuver load factor]]

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
