---
name: design_point_tw
symbol: (T/W)_dp
kind: quantity
unit: dimensionless
cluster: perf-matching
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Design-point T/W

**Definition.** Aircraft's actual static-thrust-to-weight ratio marking the design point.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
t_w = t_static / weight_n if weight_n > 0 else 0.0; ... round(t_w, 5)
```

**Inputs.**

- [[g_gravity|Standard gravity]]

**Produced by.** `app/services/matching_chart_service.py:622` — `_design_point_from_aircraft`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Feasibility verdict`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_check_feasibility:996` · `MatchingChartResponse.design_point.t_w` · `frontend/hooks/useMatchingChart.ts DesignPoint`

**Source.** 🟢 SOURCED

> Sadraey 2013 §4.3.1 steps 4-6 (matching-chart-optimization): the design point is read as (T/W)_d inside the acceptable region, and engine size follows as T = W_TO*(T/W)_d. The definition T/W = T_static_SL/W_MTOW matches the source's convention (thrust at sea level over maximum take-off weight).
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
(T/W)_d; T = W_TO * (T/W)_d
```

**⚠️ Divergence from the source.** Sadraey's design point is the OPTIMUM inside the feasible region (for jets, the smallest feasible T/W); this code instead plots the aircraft's ACTUAL T/W and tests it for feasibility. That is a legitimate and arguably more useful inversion for a design tool, but it is not the source's procedure and should not be described as 'selecting a design point'.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `# T/W = T_static_SL / W_MTOW  (static thrust at sea level over maximum take-off weight)`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
