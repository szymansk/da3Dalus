---
name: design_point_ws
symbol: (W/S)_dp
kind: quantity
unit: N/m^2
cluster: perf-matching
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Design-point W/S

**Definition.** Aircraft's actual wing loading marking the design point.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if "ws_n_m2" in aircraft: ws = float(aircraft["ws_n_m2"]) elif "s_ref_m2" in aircraft and float(aircraft["s_ref_m2"]) > 0: ws = weight_n / float(aircraft["s_ref_m2"]) else: ws = 0.0; ... round(ws, 2)
```

**Inputs.**

- [[g_gravity|Standard gravity]]

**Produced by.** `app/services/matching_chart_service.py:625` — `_design_point_from_aircraft`

**Consumed by.**

- in this graph: `Feasibility verdict`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_check_feasibility:995` · `MatchingChartResponse.design_point.ws_n_m2` · `frontend MatchingChartTab.tsx`

**Source.** 🟢 SOURCED

> Sadraey 2013 §4.3.1 steps 5-6: read (W/S)_d from the chart, then S = W_TO/(W/S)_d. Scholz 05_PreliminarySizing §5.x uses m_MTO/S_W equivalently.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
(W/S)_d; S = W_TO/(W/S)_d
```

**⚠️ Divergence from the source.** Falls back to 0.0 when geometry is missing - an impossible wing loading that plots at the chart origin, inside every feasible region, with no warning (ADR 0020). The sources have no zero-W/S case; Sadraey explicitly warns against even sweeping through W/S = 0 because the 1/(W/S) terms diverge.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Falls back to 0.0 (an impossible wing loading that plots at the chart origin) when geometry is missing, with no warning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# AR held constant during drag; S = W / (W/S), b = √(AR · S).`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
