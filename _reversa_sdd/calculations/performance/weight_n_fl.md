---
name: weight_n_fl
symbol: W
kind: quantity
unit: N
cluster: perf-matching
user_visible: false
source_status: SOURCED
---

# Aircraft weight

**Definition.** MTOW in newtons from mass and gravity.

**Formula — as the code writes it.**

```
weight_n = mass_kg * g
```

**Inputs.** [[g_gravity|Standard gravity]]

**Produced by.** `app/services/field_length_service.py:199` — `_compute_s_to_ground`

**Consumed by.**

- in this graph: [[t_over_w_fl|Thrust-to-weight (field length)]] · [[wing_loading_fl|Wing loading (field length)]]
- outside it: `wing_loading_fl:200` · `t_over_w_fl:202` · `_compute_s_ldg_ground:260`

**Source.** 🟢 SOURCED

> Scholz 05_PreliminarySizing §5.2 unit bookkeeping (SI: W and T in N, g = 9.81 m/s^2); W = m*g throughout Sadraey Ch. 4.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
W = m * g
```

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
