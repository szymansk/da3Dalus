---
name: fe_weight
symbol: W
kind: quantity
unit: N
cluster: perf-envelope
user_visible: false
source_status: SOURCED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/sourced
---

# Aircraft weight

**Definition.** Design weight used for stall speed and maneuver load factors.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
weight = mass_kg * GRAVITY
```

**Inputs.**

- [[fe_mass|Design mass (envelope)]]  — *⤵ fallback*
- [[fe_gravity|Gravitational acceleration (flight envelope)]]

**Produced by.** `app/services/flight_envelope_service.py:313` — `compute_vn_curve`

**Consumed by.**

- in this graph: `Negative maneuver load factor` · `Positive maneuver load factor` · `Stall speed (1 g)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

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
