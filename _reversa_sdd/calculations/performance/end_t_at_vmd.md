---
name: end_t_at_vmd
symbol: t(V_md)
kind: quantity
unit: s
cluster: perf-envelope
user_visible: false
source_status: PARTIAL
---

# Flight time at V_md

**Definition.** Intermediate flight time at minimum-drag speed used to build the range.

**Formula — as the code writes it.**

```
t_at_vmd_s = (capacity_wh_val * 3600.0) / p_req_vmd
```

**Inputs.** [[end_capacity_wh|Battery capacity]] · [[end_seconds_per_hour|Wh-to-Ws conversion]] · [[end_p_req_vmd|Power required at V_md]]

**Produced by.** `app/services/endurance_service.py:411` — `compute_endurance`

**Consumed by.**

- in this graph: [[end_range_max|Maximum range]]

**Source.** 🟡 PARTIAL

> Traub 2011 (as above).
>
> — via `scholz`

**The source states it as.**

```
t(V_md) = E_batt*3600/P_req(V_md)
```

**⚠️ Divergence from the source.** Same 100%-of-nameplate issue as end_t_endurance_max; feeds end_range_max.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
