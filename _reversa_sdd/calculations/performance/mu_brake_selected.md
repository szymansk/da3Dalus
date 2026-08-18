---
name: mu_brake_selected
symbol: μ
kind: quantity
unit: dimensionless
cluster: perf-matching
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/no-source-found
  - flag/divergence
---

# Selected braking friction

**Definition.** Friction coefficient chosen by the landing mode.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if landing_mode == "belly_land": mu_brake = _MU_BELLY  else: mu_brake = _MU_BRAKE_HARD
```

**Inputs.**

- [[mu_belly|Belly-landing friction]]
- [[mu_brake_hard|Braking friction, hard runway]]

**Produced by.** `app/services/field_length_service.py:430` — `compute_field_lengths`

**Consumed by.**

- in this graph: `Friction-adjusted landing coefficient`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_compute_s_ldg_ground:435`

**Source.** 🔴 NO SOURCE FOUND

> Both branch values are unsourced (see mu_brake_hard PARTIAL and mu_belly NO_SOURCE_FOUND).
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Because mu_belly (0.5) > mu_brake (0.4), the selection inverts the physical ordering: choosing 'belly_land' shortens the computed landing distance.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
