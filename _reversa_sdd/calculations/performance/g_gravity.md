---
name: g_gravity
symbol: g
kind: constant
unit: m/s^2
cluster: perf-matching
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: physical-constant
tags:
  - cluster/perf-matching
  - class/physical-constant
  - source/sourced
  - audit/confirmed
  - flag/physical
---

# Standard gravity

**Definition.** Gravitational acceleration converting mass to weight.

**Physical constant.** A value of nature. It must be identical everywhere it appears — a second definition is a defect by construction, not a judgement call.
*Identified as: gravity.*

**Value.** `9.81`

**Formula — as the code writes it.**

```
_G: float = 9.81
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/field_length_service.py:69` — `_G`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Design-point T/W` · `Design-point W/S` · `Takeoff ground roll` · `Power-loading T/W floor` · `Takeoff constraint T/W` · `Unused gravity parameter in WCL` · `Aircraft weight`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
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
