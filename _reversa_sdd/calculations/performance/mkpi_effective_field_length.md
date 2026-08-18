---
name: mkpi_effective_field_length
symbol: s_field
kind: quantity
unit: m
cluster: perf-envelope
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/scale
---

# Effective field length

**Definition.** Longer of the take-off and landing distances over the 50 ft obstacle.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
eff = max(result.get("s_to_50ft_m", 0), result.get("s_ldg_50ft_m", 0))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/mission_kpi_service.py:324` — `_compute_field_length_score`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `KPI: field friendliness` · `Field-friendliness score`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> 50 ft obstacle height: FAR Part 23 §23.53 (GA takeoff distance to 50 ft) — confirmed in Scholz 05_PreliminarySizing §5.2 and Sadraey §4.3.4, which contrast it with the 35 ft screen of CS-25/FAR-25.
>
> — via `scholz`

**The source states it as.**

```
s_field = max(s_TO_50ft, s_LDG_50ft)
```

**⚠️ Scale (ADR 0023).** ADR 0023: 15.24 m is a certification screen height for manned GA aircraft. For a 1.5 kg model with a ~1.5 m span it is roughly ten spans of climb, and no RC field imposes it — RC field length is set by the physical strip and the pilot's sightlines. The constant originates in the delegated field_length_service, so the fix belongs there, but this KPI is where it reaches the user.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** The '50 ft' (15.24 m) obstacle height is a FAR/CS-23 certification screen height carried into an RC/UAV field-length KPI (ADR 0023 scale check — constant originates in the delegated field_length_service).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
