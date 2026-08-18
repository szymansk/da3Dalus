---
name: v_stall_to
symbol: V_S,TO
kind: quantity
unit: m/s
cluster: perf-matching
user_visible: false
source_status: SOURCED
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/sourced
---

# Takeoff-configuration stall speed

**Definition.** Stall speed in takeoff configuration, falling back to the clean V_S.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
v_stall_to: float = float(aircraft.get("v_s_to_mps") or v_stall)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/field_length_service.py:367` — `compute_field_lengths`

**Consumed by.**

- in this graph: `Lift-off speed`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_v_lof:369`

**Source.** 🟢 SOURCED

> Sadraey 2013 Eq. 4.30/4.31 §4.3.2 (L = W = 0.5*rho*V_s^2*S*CL_max); Scholz 05_PreliminarySizing §5.1 gives the per-configuration form V_S,L = sqrt(2*m*g/(rho*S_W*CL_max,L)). Using a configuration-specific CL_max, hence a configuration-specific V_S, is exactly the sources' practice.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
V_S = sqrt(2*(W/S)/(rho*CL_max))
```

**Cited in the code itself.** `# gh-526: prefer the per-configuration V_s when present (cached by assumption_compute_service after one AeroBuildup pass per high-lift configuration).`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
