---
name: v_lof
symbol: V_LOF
kind: quantity
unit: m/s
cluster: perf-matching
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/sourced
  - surface/user-visible
---

# Lift-off speed

**Definition.** Speed at which the aircraft leaves the ground.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return _V_LOF_FACTOR * v_stall_mps
```

**Inputs.**

- [[v_lof_factor|Lift-off speed factor]]
- [[v_stall_to|Takeoff-configuration stall speed]]

**Produced by.** `app/services/field_length_service.py:132` — `_v_lof`

**Consumed by.**

- in this graph: `Bungee partial ground roll`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `compute_field_lengths:369` · `_compute_s_to_bungee_partial (bungee cutoff):410` · `FieldLengthRead.vto_obstacle_mps:443`

**Source.** 🟢 SOURCED

> FAR 23.51 / Sadraey Eq. 4.72 / Scholz 05_PreliminarySizing §5.2 (see v_lof_factor)
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
V_LOF = 1.2 * V_S,TO
```

**Cited in the code itself.** `"V_LOF = 1.2 · V_S (Roskam standard liftoff speed)."`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
