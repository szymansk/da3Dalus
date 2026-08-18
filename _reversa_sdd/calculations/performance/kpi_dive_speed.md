---
name: kpi_dive_speed
symbol: V_D
kind: quantity
unit: m/s
cluster: perf-envelope
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# KPI: dive speed

**Definition.** Dive-speed KPI recomputed from V_max rather than read from the curve.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
value=round(1.4 * v_max_mps, 4)
```

**Inputs.**

- [[fe_v_max|Maximum level speed]]  — *⤵ fallback*
- [[fe_dive_factor|Dive-speed factor]]

**Produced by.** `app/services/flight_envelope_service.py:523` — `derive_performance_kpis`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `PerformanceOverview.tsx`

**Source.** 🔴 NO SOURCE FOUND

> Inherits fe_dive_factor (1.4, unattributable).
>
> — via `scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Recomputes 1.4*V_max at fe:523 instead of reading vn_curve.dive_speed_mps produced ~200 lines earlier from the same input — a duplicate producer inside a single function.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Recomputes 1.4·V_max instead of consuming vn_curve.dive_speed_mps computed 200 lines earlier from the same input — duplicate producer inside one file.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
