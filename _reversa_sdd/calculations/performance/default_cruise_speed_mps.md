---
name: default_cruise_speed_mps
symbol: V_cruise
kind: constant
unit: m/s
cluster: perf-oppoints
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Default cruise speed

**Definition.** Cruise speed target used when no flight profile exists.

**Value.** `18.0`

**Formula — as the code writes it.**

```
"cruise_speed_mps": 18.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:204` — `_default_profile`

**Consumed by.**

- in this graph: [[cruise_speed_resolved|Resolved cruise speed]]
- outside it: `app/services/operating_point_generator_service.py:277, 335, 398` · `app/services/assumption_compute_service.py:1037`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 18 m/s (65 km/h) is plausible for a mid-size RC model but is not attributable to Sadraey, Scholz, Anderson, Lennon or the RC-Network wiki. Sadraey's method derives cruise speed from the mission requirement, never from a class default. Triplicated as an inline literal at lines 277/335/398.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The literal 18.0 is repeated as an inline default at lines 277, 335 and 398 rather than referenced from _default_profile.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
