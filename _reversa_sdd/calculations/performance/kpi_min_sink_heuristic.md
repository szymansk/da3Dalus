---
name: kpi_min_sink_heuristic
symbol: 1.2
kind: constant
unit: -
cluster: perf-envelope
user_visible: true
source_status: SOURCED
---

# Min-sink heuristic factor

**Definition.** Cold-start multiplier estimating minimum-sink speed from stall speed.

**Value.** `1.2`

**Formula — as the code writes it.**

```
value=round(1.2 * stall_speed_mps, 4)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/flight_envelope_service.py:474` — `derive_performance_kpis`

**Consumed by.**

- in this graph: [[kpi_min_sink_speed|KPI: min sink speed]]

**Source.** 🟢 SOURCED

> Sadraey, Aircraft Design: A Systems Engineering Approach §4.2.5.4 Eq. 4.25: V_Emax = V_Pmin ~ 1.2*V_s to 1.4*V_s. 1.2 is the low end of the stated band and is correctly applied to the minimum-power speed.
>
> — via `scholz`

**The source states it as.**

```
V_min_sink ~ 1.2 * V_s
```

**⚠️ Scale (ADR 0023).** Sadraey's band is given for GA/transport prop aircraft; no RC-scale validation. Unlike kpi_best_ld_heuristic, this one uses the right quantity from the right equation.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**Cited in the code itself.** `gh-475 audit §4.1 (see kpi_best_ld_heuristic)`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
