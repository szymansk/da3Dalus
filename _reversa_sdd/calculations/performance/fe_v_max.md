---
name: fe_v_max
symbol: V_max
kind: parameter
unit: m/s
cluster: perf-envelope
user_visible: true
source_status: PARTIAL
node_class: unclassified-parameter
tags:
  - cluster/perf-envelope
  - class/unclassified-parameter
  - source/partial
  - surface/user-visible
---

# Maximum level speed

**Definition.** Max level speed goal from the flight profile, else the 28 m/s default.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Formula — as the code writes it.**

```
v = goals.get("max_level_speed_mps"); return float(v) if v is not None else 28.0
```

**Inputs.**

- [[fe_v_max_default|Default maximum level speed]]  — *⤵ fallback*

**Produced by.** `app/services/flight_envelope_service.py:580` — `_get_v_max`

**Consumed by.**

- in this graph: `Dive speed` · `KPI: dive speed` · `KPI: max speed`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟡 PARTIAL

> When present, a user-declared goal (max_level_speed_mps) — provenance is the user's. Only the fallback path is unsourced.
>
> — via `rc`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
