---
name: mission_min_tw_table
symbol: (T/W)_mission
kind: constant
unit: dimensionless
cluster: perf-matching
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/perf-matching
  - class/unclassified-constant
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Mission-min T/W table

**Definition.** Fixed T/W floors per mission profile.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `acro_3d:1.5; wing_racer:0.8; sport:0.5`

**Formula — as the code writes it.**

```
_MISSION_MIN_TW_BY_PROFILE: dict[str, float] = {"acro_3d": 1.5, "wing_racer": 0.8, "sport": 0.5}
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/matching_chart_service.py:448` — `_MISSION_MIN_TW_BY_PROFILE`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Effective constraint keys (custom fallback)` · `Mission-min T/W floor`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_mission_min_tw_constraint:494` · `_build_rc_additive_constraints:1074,1086,1088`

**Source.** 🟡 PARTIAL

> Nothing in the lead authority. Scholz and Sadraey have no acro/3D mission class and no fixed T/W floor by mission. The in-code attribution is to Lennon, 'Basics of R/C Model Aircraft Design' (1996) Ch. 19 - hobbyist-tier (rc-aircraft-designer authority level) and NOT verified against that text in this pass.
>
> — via `aircraft-design-scholz (no coverage; in-code Lennon Ch.19 claim unverified)`

**⚠️ Divergence from the source.** T/W >= 1 as the hover condition for 3D aerobatics is genuine, widely-held RC practice and is physically self-evident (sustained vertical hover requires thrust >= weight). The specific values 1.5 / 0.8 / 0.5 are not attributable from the sources consulted here.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Inverse of the usual problem - this constant is RC-native and has no transport-category equivalent, so it cannot be cross-checked against the academic authority at all. It should be labelled a mission convention, not a derived constraint.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** This dict doubles as the 'effective_keys' fallback at line 1077, where its PROFILE names are compared against CONSTRAINT keys — a name/role contradiction that silently disables the vertical-climb additive for custom profiles.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Mission-min T/W defaults (horizontal line at fixed T/W). Higher numbers come from acro / 3D / unlimited mission convention (Lennon Ch. 19).`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
