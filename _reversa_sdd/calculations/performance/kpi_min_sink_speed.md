---
name: kpi_min_sink_speed
symbol: V_min_sink
kind: quantity
unit: m/s
cluster: perf-envelope
user_visible: true
source_status: SOURCED
---

# KPI: min sink speed

**Definition.** Minimum-power speed from a trimmed marker, else the cached polar value, else 1.2·V_s.

**Formula — as the code writes it.**

```
marker.velocity_mps | v_min_sink_polar_mps | 1.2 * stall_speed_mps
```

**Inputs.** [[fe_v_stall|Stall speed (1 g)]] · [[kpi_min_sink_heuristic|Min-sink heuristic factor]]

**Produced by.** `app/services/flight_envelope_service.py:446` — `derive_performance_kpis`

**Consumed by.**

- outside it: `PerformanceOverview.tsx`

**Source.** 🟢 SOURCED

> Polar branch derived upstream; heuristic branch is Sadraey Eq. 4.25 (see kpi_min_sink_heuristic).
>
> — via `scholz`

**⚠️ Divergence from the source.** Same unreachable 'min_sink' marker branch as kpi_best_ld_speed (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Same unreachable 'min_sink' marker branch as kpi_best_ld_speed.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
