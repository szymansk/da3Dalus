---
name: feasibility_verdict
symbol: feasibility
kind: quantity
unit: enum
cluster: perf-matching
user_visible: true
source_status: PARTIAL
---

# Feasibility verdict

**Definition.** Whether the design point satisfies all applicable, warning-relevant constraints.

**Formula — as the code writes it.**

```
feasibility = "infeasible_below_constraints" if infeasible else "feasible"
```

**Inputs.** [[design_point_ws|Design-point W/S]] · [[design_point_tw|Design-point T/W]] · [[tol_line_binding|Line-constraint binding tolerance]] · [[tol_vert_binding|Vertical-constraint binding tolerance]]

**Produced by.** `app/services/matching_chart_service.py:687` — `_check_feasibility`

**Consumed by.**

- in this graph: [[binding_flag_propagation|Binding-flag back-propagation]]
- outside it: `compute_chart:994` · `MatchingChartResponse.feasibility` · `frontend/hooks/useMatchingChart.ts Feasibility`

**Source.** 🟡 PARTIAL

> Sadraey 2013 §4.3.1 step 3 (matching-chart-optimization): 'A design point is feasible only when it lies on the satisfying side of every constraint simultaneously.' The acceptable-region logic table (left of stall/landing verticals, above takeoff/ROC/climb curves for jets) is sourced. The tolerances are not.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
feasible <=> design point on the satisfying side of every applicable constraint
```

**⚠️ Divergence from the source.** Nearest-neighbour lookup (min over \|ws_range[i] - ws_dp\|) instead of interpolation, despite the comment saying 'Interpolate'. With 200 points over 10-1500 N/m^2 the grid spacing is ~7.5 N/m^2, which at an RC design point of ~50 N/m^2 is a ~15% quantisation error in W/S - large enough to flip a verdict.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Nearest-neighbour lookup (min over \|ws_range[i] - ws_dp\|) instead of interpolation despite the comment saying 'Interpolate constraint T/W at the design point W/S'.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
