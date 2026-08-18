---
name: end_seconds_per_hour
symbol: 3600
kind: constant
unit: s/h
cluster: perf-envelope
user_visible: false
source_status: SOURCED
---

# Wh-to-Ws conversion

**Definition.** Seconds per hour converting battery capacity in Wh to joules.

**Value.** `3600.0`

**Formula — as the code writes it.**

```
(capacity_wh_val * 3600.0) / p_req_vmin
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/endurance_service.py:403` — `compute_endurance`

**Consumed by.**

- in this graph: [[end_t_at_vmd|Flight time at V_md]] · [[end_t_endurance_max|Maximum endurance]]

**Source.** 🟢 SOURCED

> SI unit conversion.
>
> — via `scholz`

**The source states it as.**

```
3600 s/h
```

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
