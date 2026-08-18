---
name: effective_field_length
symbol: s_field_eff
kind: quantity
unit: m
cluster: perf-matching
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Effective field length

**Definition.** Worse of takeoff and landing 50-ft distances, used as the field-friendliness KPI numerator.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
eff = max(result.get("s_to_50ft_m", 0), result.get("s_ldg_50ft_m", 0))
```

**Inputs.**

- [[s_to_50ft|Takeoff distance over 50 ft]]
- [[s_ldg_50ft|Landing distance from 50 ft]]

**Produced by.** `app/services/mission_kpi_service.py:324` — `_compute_field_length_score`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `_kpi_field_friendliness:340` · `MissionAxisKpi → mission KPI API → UI`

**Source.** 🔴 NO SOURCE FOUND

> No source. Scholz 05_PreliminarySizing and Sadraey §4.3.1 treat s_TOFL and s_LFL as two SEPARATE constraints on the matching chart (one a sloped T/W line, one a vertical W/S limit); neither collapses them into a max().
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Reducing two structurally different constraints to a single max() discards the information the matching chart exists to show - which of the two is binding, and in which variable. It is an app KPI convention, not a method from the literature.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `formula = "max(s_TO_50ft, s_LDG_50ft); score = target / effective"`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
