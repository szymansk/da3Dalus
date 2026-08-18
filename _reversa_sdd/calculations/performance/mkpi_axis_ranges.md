---
name: mkpi_axis_ranges
symbol: [lo, hi]
kind: parameter
unit: varies
cluster: perf-envelope
user_visible: true
source_status: SOURCED
node_class: unclassified-parameter
tags:
  - cluster/perf-envelope
  - class/unclassified-parameter
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Mission axis ranges

**Definition.** Per-axis normalisation bounds taken from the primary mission preset row.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Formula — as the code writes it.**

```
rng = primary_preset.axis_ranges  (fallback chain: presets[active_mission_ids[0]] -> presets['trainer'] -> RuntimeError)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/mission_kpi_service.py:448` — `compute_mission_kpis`

**Consumed by.**

- in this graph: `Axis normalisation` · `Soll polygon scores`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> Per-mission preset rows — provenance belongs to the mission-preset data, not to this cluster.
>
> — via `scholz`

**⚠️ Divergence from the source.** ADR 0020 undeclared substitution: an unknown mission id silently falls back to the 'trainer' preset (mkpi:432) while the response still echoes the REQUESTED active_mission_id. The radar is then normalised against a mission the user did not select, and the response asserts otherwise.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Undeclared substitution: an unknown mission id silently falls back to the 'trainer' preset's ranges (line 432) and the response still echoes the requested active_mission_id — the radar is normalised against a mission the user did not select, with no warning.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
