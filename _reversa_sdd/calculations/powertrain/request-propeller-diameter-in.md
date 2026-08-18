---
name: request-propeller-diameter-in
symbol: propeller_diameter_in
kind: parameter
unit: in
cluster: powertrain
user_visible: true
source_status: SOURCED
node_class: unclassified-parameter
tags:
  - cluster/powertrain
  - class/unclassified-parameter
  - source/sourced
  - surface/user-visible
---

# Propeller diameter input

**Definition.** Propeller diameter in inches, taken from the propeller_polars header row.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_performance.py:215` — `PowertrainPerformanceRequest.propeller_diameter_in`

**Consumed by.**

- in this graph: `Propeller diameter in metres`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:646` · `app/api/v2/endpoints/aeroplane/powertrain_performance.py:245`

**Source.** 🟢 SOURCED

> Roxxy Motoren-Fibel, Ch. 1, pp. 6-7: 'In RC model aircraft design, propeller characteristics are standardized using measurements in inches. The first number denotes the diameter and the second the pitch ... a 10 x 5 propeller has a 10-inch diameter and a 5-inch pitch.' Diameter primarily influences thrust force.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
Propeller designation = Diameter[in] x Pitch[in]
```

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
