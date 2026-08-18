---
name: kpi_max_speed
symbol: V_max
kind: quantity
unit: m/s
cluster: perf-envelope
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# KPI: max speed

**Definition.** Maximum level speed echoed as a KPI with confidence 'limit'.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
value=round(v_max_mps, 4)
```

**Inputs.**

- [[fe_v_max|Maximum level speed]]  — *⤵ fallback*

**Produced by.** `app/services/flight_envelope_service.py:486` — `derive_performance_kpis`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `PerformanceOverview.tsx`

**Source.** 🟡 PARTIAL

> Pass-through of fe_v_max — sourced when the user declares a goal, unsourced (28.0) otherwise.
>
> — via `rc`

**⚠️ Divergence from the source.** Reported with confidence 'limit' even when it is the invented 28.0 default.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
