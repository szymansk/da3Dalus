---
name: g_gravity
symbol: g
kind: constant
unit: m/s^2
cluster: perf-matching
user_visible: false
source_status: SOURCED
---

# Standard gravity

**Definition.** Gravitational acceleration converting mass to weight.

**Value.** `9.81`

**Formula — as the code writes it.**

```
_G: float = 9.81
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/field_length_service.py:69` — `_G`

**Consumed by.**

- in this graph: [[design_point_tw|Design-point T/W]] · [[design_point_ws|Design-point W/S]] · [[s_to_ground|Takeoff ground roll]] · [[tw_power_loading|Power-loading T/W floor]] · [[tw_takeoff_constraint|Takeoff constraint T/W]] · [[wcl_g_unused|Unused gravity parameter in WCL]] · [[weight_n_fl|Aircraft weight]]
- outside it: `_compute_s_to_ground` · `_compute_s_ldg_ground` · `matching_chart_service.py:40 (imported)` · `_takeoff_constraint` · `_power_loading_constraint` · `_design_point_from_aircraft`

**Source.** 🟢 SOURCED

> Scholz, 05_PreliminarySizing §5.2 unit bookkeeping: 'SI: ... g = 9.81 m/s^2' (British: 32.17 ft/s^2)
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
g = 9.81 m/s^2
```

**Cited in the code itself.** `# m/s² — standard gravity`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
