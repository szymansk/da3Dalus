---
name: kpi_best_ld_speed
symbol: V_md
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
  - flag/anomaly
  - flag/divergence
---

# KPI: best L/D speed

**Definition.** Minimum-drag speed from a trimmed marker, else the cached polar value, else 1.4·V_s.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
marker.velocity_mps | v_md_polar_mps | 1.4 * stall_speed_mps
```

**Inputs.**

- [[fe_v_stall|Stall speed (1 g)]]  — *⊣ limit*
- [[kpi_best_ld_heuristic|Best-L/D heuristic factor]]

**Produced by.** `app/services/flight_envelope_service.py:410` — `derive_performance_kpis`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `PerformanceOverview.tsx`

**Source.** 🟡 PARTIAL

> Polar branch (ctx v_md) is properly derived upstream; heuristic branch inherits kpi_best_ld_heuristic.
>
> — via `scholz`

**⚠️ Divergence from the source.** The 'trimmed' branch is unreachable: markers_by_label is keyed on op.name (fe:614) and nothing in app/ ever creates an operating point named 'best_ld'. The whole confidence='trimmed' tier is dead (ADR 0021). Separately the docstring promises a 'TRIMMED operating-point marker' but marker.status is never read, so a NOT_TRIMMED point would still be labelled 'trimmed' if the branch were ever reachable.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The 'trimmed' branch is unreachable in practice: markers_by_label is keyed on op.name (line 614), and no producer anywhere in app/ ever creates an operating point named 'best_ld' (grep confirms the literal appears only at lines 410/446/494 and in a schema docstring). Worse, the docstring promises 'TRIMMED operating-point marker' but the code never inspects marker.status — a NOT_TRIMMED point would still be labelled confidence='trimmed'.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
