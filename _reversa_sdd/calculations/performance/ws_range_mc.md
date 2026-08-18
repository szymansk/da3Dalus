---
name: ws_range_mc
symbol: W/S[i]
kind: quantity
unit: N/m^2
cluster: perf-matching
user_visible: true
source_status: PARTIAL
---

# W/S sweep vector

**Definition.** Linear W/S sample vector forming the chart's x-axis.

**Formula — as the code writes it.**

```
ws_range = [_WS_MIN + (_WS_MAX - _WS_MIN) * i / (_WS_STEPS - 1) for i in range(_WS_STEPS)]
```

**Inputs.** [[ws_sweep_min|W/S sweep lower bound]] · [[ws_sweep_max|W/S sweep upper bound]] · [[ws_sweep_steps|W/S sweep resolution]]

**Produced by.** `app/services/matching_chart_service.py:838` — `compute_chart`

**Consumed by.**

- in this graph: [[tw_climb_constraint|Climb constraint T/W]] · [[tw_cruise_constraint|Cruise constraint T/W]] · [[tw_takeoff_constraint|Takeoff constraint T/W]] · [[tw_vertical_climb|Vertical-climb T/W]] · [[v_md|Minimum-drag speed]]
- outside it: `all t_w_points lists` · `MatchingChartResponse.ws_range_n_m2` · `frontend/hooks/useMatchingChart.ts` · `frontend/components/workbench/MatchingChartTab.tsx`

**Source.** 🟡 PARTIAL

> Sweeping W/S as the chart abscissa is SOURCED: Sadraey 2013 §4.3.1 step 2. The specific linear 10-1500 N/m^2 / 200-point vector is not.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
Sadraey §4.3.1 step 2: plot all constraint curves against a W/S sweep
```

**⚠️ Divergence from the source.** Endpoints violate the source's own guidance in both directions (see ws_sweep_min, ws_sweep_max).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Inherits the transport-scale axis range.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
