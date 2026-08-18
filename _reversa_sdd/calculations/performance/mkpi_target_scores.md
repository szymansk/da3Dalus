---
name: mkpi_target_scores
symbol: scores_0_1
kind: quantity
unit: -
cluster: perf-envelope
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Soll polygon scores

**Definition.** Target polygon derived from the user's editable mission objective, normalised with the same axis ranges as the Ist polygon.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
_normalise_score(objective.target_stall_safety, *axis_ranges["stall_safety"]) ... target_glide_ld, target_climb_energy, target_cruise_mps, target_maneuver_n, target_wing_loading_n_m2
```

**Inputs.**

- [[mkpi_normalise_score|Axis normalisation]]
- [[mkpi_axis_ranges|Mission axis ranges]]  — *⊣ limit*

**Produced by.** `app/services/mission_kpi_service.py:374` — `_objective_target_scores`

**Consumed by.**

- outside it: `MissionRadarChart.tsx`

**Source.** 🟢 SOURCED

> Normalised with the same _normalise_score and axis_ranges as the matching Ist axis (gh-767), which is what makes the Soll and Ist polygons directly comparable.
>
> — via `scholz`

**⚠️ Divergence from the source.** Correct by design for the primary polygon. But only the polygon whose mission id equals objective.mission_type uses live user targets (mkpi:480); every comparison overlay uses the static preset.target_polygon. Two visually identical white lines are produced by two different mechanisms, and nothing in the UI distinguishes them.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Only the polygon whose mission id equals objective.mission_type uses the live user targets (line 480); every comparison overlay uses the static preset.target_polygon, so two visually identical white/overlay lines are produced by two different mechanisms.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"gh-767: each score is normalised with the *same* _normalise_score and axis_ranges the matching Ist axis uses, so the white Soll line and the orange Ist polygon stay directly comparable"`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
