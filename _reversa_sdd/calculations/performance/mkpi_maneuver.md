---
name: mkpi_maneuver
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

# KPI: maximum load factor

**Definition.** Peak positive load factor read from the cached context.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
n_max = ctx.get("flight_envelope_n_max")
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/mission_kpi_service.py:247` — `_kpi_maneuver`

**Consumed by.**

- outside it: `MissionRadarChart.tsx` · `AxisDrawer.tsx`

**Source.** 🟡 PARTIAL

> ctx['flight_envelope_n_max'] is the raw g_limit design assumption (written at assumption_compute_service:719), so this inherits fe_g_limit — Sadraey §10.4.1 Table 10.9 (RC 1.5-2, sizing convention) vs Lennon Ch. 21 (6-12 g actual pull-out loads).
>
> — via `scholz, rc`

**⚠️ Divergence from the source.** The UI formula string 'n_max from V-n diagram (load factor)' is FALSE — no V-n curve is consulted; the producer's own comment concedes this ('a physics-aware refinement reading the V-n curve's gust-augmented peak can replace this later'). Two consequences: the displayed provenance is wrong, and the gust-critical case where real n_max exceeds g_limit is invisible on this axis — precisely the case the flight-envelope service works hardest to detect. Second producer of the same user-visible n_max as kpi_max_load_factor (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Name and UI formula string both claim the V-n diagram, but ctx['flight_envelope_n_max'] is written by assumption_compute_service.py:719 as the raw g_limit design assumption — the producer's own comment says so ('A physics-aware refinement reading the V-n curve's gust-augmented peak can replace this later'). The displayed formula is false, and the gust-critical case where the real n_max exceeds g_limit is invisible on this axis.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `formula string exposed to the UI: "n_max from V-n diagram (load factor)"`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
