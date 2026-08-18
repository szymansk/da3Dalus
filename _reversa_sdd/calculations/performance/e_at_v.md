---
name: e_at_v
symbol: e(V)
kind: quantity
unit: dimensionless
cluster: perf-matching
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Reynolds-dependent Oswald factor

**Definition.** Oswald factor looked up at a given speed from the polar Re-table, or the scalar fallback.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if polar_re_table and mac_m and float(mac_m) > 0: from app.services.polar_re_table_service import lookup_e_oswald_at_v; return lookup_e_oswald_at_v(v_mps=v, table=polar_re_table); return e
```

**Inputs.**

- [[e_resolved|Resolved Oswald factor]]  — *⤵ fallback*

**Produced by.** `app/services/matching_chart_service.py:825` — `_e_at_v`

**Consumed by.**

- outside it: `e_cruise:835` · `_climb_tw_at_ws:860`

**Source.** 🟡 PARTIAL

> Same as cd0_at_v: Sadraey Eq. 4.41 uses a single scalar e (0.7-0.95); no source models e(Re) in a matching chart.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
Sadraey Eq. 4.41: single scalar e
```

**⚠️ Divergence from the source.** Same dead branch as cd0_at_v - no API caller supplies polar_re_table, so the scalar fallback always wins (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Same dead branch as cd0_at_v — no API caller supplies polar_re_table.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# gh-493 Amendment 7 (see _cd0_at_v)`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
