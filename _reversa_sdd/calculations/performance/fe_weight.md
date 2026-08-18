---
name: fe_weight
symbol: W
kind: quantity
unit: N
cluster: perf-envelope
user_visible: false
source_status: SOURCED
---

# Aircraft weight

**Definition.** Design weight used for stall speed and maneuver load factors.

**Formula — as the code writes it.**

```
weight = mass_kg * GRAVITY
```

**Inputs.** [[fe_mass|Design mass (envelope)]] · [[fe_gravity|Gravitational acceleration (flight envelope)]]

**Produced by.** `app/services/flight_envelope_service.py:313` — `compute_vn_curve`

**Consumed by.**

- in this graph: [[fe_n_neg_maneuver|Negative maneuver load factor]] · [[fe_n_pos_maneuver|Positive maneuver load factor]] · [[fe_v_stall|Stall speed (1 g)]]

**Source.** 🟢 SOURCED

> Definitional.
>
> — via `scholz`

**The source states it as.**

```
W = m*g
```

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
