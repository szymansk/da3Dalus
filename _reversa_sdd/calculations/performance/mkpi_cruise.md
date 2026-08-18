---
name: mkpi_cruise
symbol: V_cruise
kind: quantity
unit: m/s
cluster: perf-envelope
user_visible: true
source_status: SOURCED
---

# KPI: cruise speed

**Definition.** Cruise speed passed through from the computation context.

**Formula — as the code writes it.**

```
v = _ctx_get(ctx, "v_cruise_mps")
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/mission_kpi_service.py:236` — `_kpi_cruise`

**Consumed by.**

- outside it: `MissionRadarChart.tsx` · `AxisDrawer.tsx`

**Source.** 🟢 SOURCED

> Pass-through of ctx v_cruise_mps — provenance belongs upstream.
>
> — via `scholz`

**⚠️ Divergence from the source.** Notable that mission_kpi reads this genuine cruise speed while flight_envelope_service ignores it and back-derives its own V_C from V_max (see fe_v_c). The correct value already exists in the context.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
