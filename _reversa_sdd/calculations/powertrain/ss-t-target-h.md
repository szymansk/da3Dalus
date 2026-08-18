---
name: ss-t-target-h
symbol: t_target_h
kind: quantity
unit: h
cluster: powertrain
user_visible: false
source_status: PARTIAL
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/partial
---

# Target flight time in hours

**Definition.** Mission duration converted from minutes for the energy budget.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
t_target_h = t_target_min / 60.0
```

**Inputs.**

- [[ss-t-target-min|Target flight time]]  — *⊣ limit*

**Produced by.** `app/services/powertrain_solution_space_service.py:352` — `compute_solution_space`

**Consumed by.**

- in this graph: `Mission energy at high prop efficiency` · `Mission energy at low prop efficiency` · `Required mission energy`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:377` · `app/services/powertrain_solution_space_service.py:400` · `app/services/powertrain_solution_space_service.py:412`

**Source.** 🟡 PARTIAL

> Unit conversion only (min -> h). Sadraey (2013) §8.7 gives the only endurance anchor for this class: a 2-hp electric motor needs ~400 g of battery for 15 minutes, and 'the highest practical battery output is typically less than about 100 hp for less than an hour'.
>
> — via `aircraft-design-scholz`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
