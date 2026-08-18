---
name: mkpi_target_field_length
symbol: s_field,target
kind: parameter
unit: m
cluster: perf-envelope
user_visible: true
source_status: SOURCED
---

# Target field length

**Definition.** User-declared acceptable field length from the persisted MissionObjective.

**Formula — as the code writes it.**

```
objective.target_field_length_m
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/mission_kpi_service.py:464` — `compute_mission_kpis`

**Consumed by.**

- in this graph: [[mkpi_field_score|Field-friendliness score]]

**Source.** 🟢 SOURCED

> User-declared value on the persisted MissionObjective — provenance is the user's, which is the correct authority for a target.
>
> — via `rc`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
