---
name: fe_v_max
symbol: V_max
kind: parameter
unit: m/s
cluster: perf-envelope
user_visible: true
source_status: PARTIAL
---

# Maximum level speed

**Definition.** Max level speed goal from the flight profile, else the 28 m/s default.

**Formula — as the code writes it.**

```
v = goals.get("max_level_speed_mps"); return float(v) if v is not None else 28.0
```

**Inputs.** [[fe_v_max_default|Default maximum level speed]]

**Produced by.** `app/services/flight_envelope_service.py:580` — `_get_v_max`

**Consumed by.**

- in this graph: [[fe_v_dive|Dive speed]] · [[kpi_dive_speed|KPI: dive speed]] · [[kpi_max_speed|KPI: max speed]]

**Source.** 🟡 PARTIAL

> When present, a user-declared goal (max_level_speed_mps) — provenance is the user's. Only the fallback path is unsourced.
>
> — via `rc`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
