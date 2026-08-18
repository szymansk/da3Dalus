---
name: kpi_max_load_factor
symbol: n_max
kind: quantity
unit: g
cluster: perf-envelope
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# KPI: max load factor

**Definition.** Peak load factor from a 'max_turn' marker, else the g-limit assumption.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
max_turn_marker.load_factor | round(g_limit, 4)
```

**Inputs.**

- [[fe_g_limit|Structural limit load factor]]  — *⤵ fallback*
- [[fe_marker_load_factor|Operating-point marker load factor]]

**Produced by.** `app/services/flight_envelope_service.py:494` — `derive_performance_kpis`

**Consumed by.**

- outside it: `PerformanceOverview.tsx`

**Source.** 🟡 PARTIAL

> Falls back to fe_g_limit — see fe_g_limit for the Sadraey Table 10.9 / Lennon Ch. 21 split.
>
> — via `scholz, rc`

**⚠️ Divergence from the source.** Second producer of the same user-visible n_max as mkpi_maneuver, which reads ctx['flight_envelope_n_max'] (also just g_limit, written at assumption_compute_service:719). One quantity, two authorities, two UI surfaces (ADR 0022). The 'max_turn' marker branch is unreachable, and if it were reached it would return the hardcoded 1.0 of fe_marker_load_factor.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Second producer of the same user-visible number as mission_kpi_service._kpi_maneuver, which reads ctx['flight_envelope_n_max'] — also the g_limit assumption (assumption_compute_service line 719). One quantity, two authorities, two UI surfaces (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
