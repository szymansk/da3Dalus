---
name: s_to_50ft
symbol: s_TO_50ft
kind: quantity
unit: m
cluster: perf-matching
user_visible: true
source_status: PARTIAL
---

# Takeoff distance over 50 ft

**Definition.** Total takeoff distance to clear a 50-ft obstacle.

**Formula — as the code writes it.**

```
s_to_50ft = _apply_obstacle_factor(s_to_ground, _K_TO_50FT)
```

**Inputs.** [[s_to_ground|Takeoff ground roll]] · [[k_to_50ft|Takeoff 50-ft obstacle factor]]

**Produced by.** `app/services/field_length_service.py:425` — `compute_field_lengths`

**Consumed by.**

- in this graph: [[effective_field_length|Effective field length]]
- outside it: `FieldLengthRead.s_to_50ft_m:440` · `mission_kpi_service.py:324 (field_friendliness)` · `app/api/v2/endpoints/aeroplane/field_lengths.py:209`

**Source.** 🟡 PARTIAL

> The quantity 'takeoff distance to clear a 50 ft obstacle' is SOURCED to FAR Part 23 §23.53 (Scholz 05_PreliminarySizing §5.2). The multiplier 1.66 used to produce it is only PARTIAL (see k_to_50ft).
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
s_TO to 50 ft obstacle (FAR-23); CS-25/FAR-25 use 35 ft
```

**⚠️ Scale (ADR 0023).** A manned-GA certification distance being reported as a design KPI for 0.5-15 kg aircraft, and fed onward into the mission field_friendliness score.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**Cited in the code itself.** `"s_TO_50ft = _K_TO_50FT · s_TO_ground   (_K_TO_50FT = 1.66, SE-piston AEO)"`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
