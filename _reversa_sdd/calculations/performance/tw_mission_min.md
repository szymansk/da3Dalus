---
name: tw_mission_min
symbol: (T/W)_min
kind: quantity
unit: dimensionless
cluster: perf-matching
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Mission-min T/W floor

**Definition.** Horizontal T/W floor line from the mission profile's convention.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return _MISSION_MIN_TW_BY_PROFILE.get(profile_key)
```

**Inputs.**

- [[mission_min_tw_table|Mission-min T/W table]]  — *⊣ limit*

**Produced by.** `app/services/matching_chart_service.py:494` — `_mission_min_tw_constraint`

**Consumed by.**

- outside it: `_build_rc_additive_constraints:1086,1088` · `constraints 'Mission-Min T/W':1092` · `MatchingChartResponse.constraints`

**Source.** 🟡 PARTIAL

> Inherits mission_min_tw_table: no coverage in Scholz or Sadraey; in-code Lennon Ch.19 attribution unverified. The T/W >= 1 hover condition for 3D is physically self-evident.
>
> — via `aircraft-design-scholz (no coverage)`

**⚠️ Divergence from the source.** For an unknown/custom profile the builder silently substitutes the STRICTEST target (acro_3d = 1.5), so a custom design is judged against a 3D-hover requirement with no warning (ADR 0020). Substituting the strictest value is the opposite of the sources' practice, where an unspecified requirement simply produces no constraint line.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** For an unknown/custom profile the builder silently substitutes the STRICTEST target (acro_3d = 1.5) at line 1088, so a custom design is judged against a 3D-hover requirement with no warning.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"For 3D acro this is the **hover** condition T/W ≥ 1.5." ; hover_text:1102 "(Lennon Ch. 19 / mission convention)"`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
