---
name: fe_v_sweep
symbol: V_i
kind: quantity
unit: m/s
cluster: perf-envelope
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/sourced
  - surface/user-visible
---

# Velocity sweep points

**Definition.** Linear velocity sampling from stall to dive speed for both maneuver and gust lines.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
v = v_stall + (v_dive - v_stall) * i / (n_points - 1)
```

**Inputs.**

- [[fe_v_stall|Stall speed (1 g)]]  — *⊣ limit*
- [[fe_v_dive|Dive speed]]  — *⊣ limit*
- [[fe_n_points|V-n sampling resolution]]  — *⊣ limit*

**Produced by.** `app/services/flight_envelope_service.py:324` — `compute_vn_curve / _build_gust_lines`

**Consumed by.**

- in this graph: `Gust load-factor increment` · `Dynamic pressure` · `Gust velocity schedule`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> Numerical discretisation, no engineering source required.
>
> — via `scholz`

**The source states it as.**

```
linear sampling V_s -> V_D
```

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
