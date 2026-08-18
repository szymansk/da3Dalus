---
name: s_ldg_50ft
symbol: s_LDG_50ft
kind: quantity
unit: m
cluster: perf-matching
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Landing distance from 50 ft

**Definition.** Total landing distance from a 50-ft obstacle to full stop.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
s_ldg_50ft = _apply_obstacle_factor(s_ldg_ground, _K_LDG_50FT)
```

**Inputs.**

- [[s_ldg_ground|Landing ground roll]]
- [[k_ldg_50ft|Landing 50-ft obstacle factor]]

**Produced by.** `app/services/field_length_service.py:436` — `compute_field_lengths`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Effective field length`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `FieldLengthRead.s_ldg_50ft_m:442` · `mission_kpi_service.py:324 (field_friendliness)`

**Source.** 🟡 PARTIAL

> The quantity 'landing distance from 50 ft to full stop' is SOURCED to CS 25.125 (Scholz 05_PreliminarySizing §5.1); FAR-23 also uses 50 ft. The multiplier 2.73 is NO_SOURCE_FOUND (see k_ldg_50ft).
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
CS 25.125: horizontal distance from 50 ft to full stop at approach CAS >= 1.3*V_S
```

**⚠️ Divergence from the source.** Confirms the inventory's ADR 0022 finding: assumption_compute_service.py:787 independently produces context['landing_field_length_m'] with its own surface table and safety factor. Two producers of one user-visible landing distance, neither reconcilable to the other's source.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Both the 50 ft height and the 2.73 multiplier are manned-aircraft artefacts (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** A second, independent landing-distance authority exists — assumption_compute_service.py:787 writes context['landing_field_length_m'] from _compute_landing_field_length (gh-477) — two producers of the same user-visible number (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"s_LDG_50ft = _K_LDG_50FT · s_LDG_ground   (_K_LDG_50FT = 2.73)"`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
