---
name: analysis-goals
symbol: —
kind: constant
unit: – (mapping)
cluster: stability
user_visible: true
source_status: PARTIAL
node_class: regulatory-constant
tags:
  - cluster/stability
  - class/regulatory-constant
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Operating-point analysis goals

**Definition.** Human-readable question each named operating point is meant to answer.

**Regulatory constant.** Taken from a standard. It carries the clause *and* the class of aircraft that clause applies to.

**Value.** `14 entries: stall_near_clean, takeoff_climb, cruise, loiter_endurance, max_level_speed, approach_landing, turn_20, turn_40, turn_60, dutch_role_start, best_angle_climb_vx, best_rate_climb_vy, max_range, stall_with_flaps`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/trim_enrichment_service.py:40` — `ANALYSIS_GOALS`

**Consumed by.**

- outside it: `app/services/trim_enrichment_service.py:402` · `frontend/components/workbench/trim-interpretation/AnalysisGoalCard.tsx`

**Source.** 🟡 PARTIAL

> The individual flight conditions are all standard and citable: stall/V_S and approach V_APP ≥ 1.3·V_S — Scholz 05_PreliminarySizing §5.1 (CS 25.125); take-off climb and climb gradients — Scholz 05_PreliminarySizing (CS-25 constraints); best-angle V_x and best-rate V_y climb, max range and loiter/endurance — Scholz 05_PreliminarySizing / Breguet range; Dutch roll — Sadraey §12.3.3 and the Dutch-roll oscillation treatment. The mapping of each to a plain-English question is editorial and has no source.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
—
```

**⚠️ Divergence from the source.** Editorial UI copy over sourced flight conditions. The key 'dutch_role_start' is a typo for 'dutch_roll' and is repeated in generate_result_summary (line 370), so the misspelling is load-bearing across both dictionaries and a correctly named operating point falls back to the generic default.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Key 'dutch_role_start' is a typo for 'dutch_roll' and is repeated in generate_result_summary (line 370), so the misspelling is load-bearing across both dictionaries and any correctly named operating point falls back to the generic default.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
