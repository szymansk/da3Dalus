---
name: kpi_stall_speed
symbol: V_s
kind: quantity
unit: m/s
cluster: perf-envelope
user_visible: true
source_status: SOURCED
---

# KPI: stall speed

**Definition.** Stall-speed KPI card, always confidence 'limit'.

**Formula — as the code writes it.**

```
value=round(stall_speed_mps, 4), confidence="limit"
```

**Inputs.** [[fe_v_stall|Stall speed (1 g)]]

**Produced by.** `app/services/flight_envelope_service.py:402` — `derive_performance_kpis`

**Consumed by.**

- outside it: `PerformanceOverview.tsx` · `MCP get_flight_envelope`

**Source.** 🟢 SOURCED

> Inherits fe_v_stall (L = W inversion; Anderson, Introduction to Flight, Ch. 6).
>
> — via `aero`

**⚠️ Divergence from the source.** Confidence is hardcoded 'limit' although the value inherits fe_cl_max's unvalidated 1.4 default and fe_mass's 1.5 kg seed. A defaulted input producing a 'limit'-confidence output overstates certainty.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
