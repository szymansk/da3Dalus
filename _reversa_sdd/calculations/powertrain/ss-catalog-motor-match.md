---
name: ss-catalog-motor-match
symbol: has_motor_match
kind: quantity
unit: boolean
cluster: powertrain
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Catalog motor match flag

**Definition.** True when at least one catalog brushless_motor's rated power meets the required peak shaft power.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
max_power = specs.get("max_power_w") or specs.get("max_continuous_power_w") ; if max_power is not None and float(max_power) >= motor_shaft_peak_w: return True
```

**Inputs.**

- [[ss-motor-peak-shaft|Required motor peak shaft power]]

**Produced by.** `app/services/powertrain_solution_space_service.py:205` — `_catalog_motor_match`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/powertrain_solution_space_service.py:456` · `frontend/components/workbench/PowertrainTab.tsx:553` · `frontend/components/workbench/PowertrainTab.tsx:600`

**Source.** 🟢 SOURCED

> Roxxy Motoren-Fibel, Ch. 3, pp. 28-29: 'A motor's ability to sustain high power output for extended periods is limited by how much heat it can generate without exceeding safe temperature thresholds ... this is why proper airflow around the motor and careful attention to continuous vs. burst power ratings are critical in aircraft design.' Above 150 degC the copper enamel melts and the motor fails.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
Motor rating is thermally bounded; continuous and burst ratings are distinct quantities
```

**⚠️ Divergence from the source.** The code falls back from max_power_w to max_continuous_power_w with 'or', comparing a CONTINUOUS rating against a PEAK requirement whenever the burst figure is missing. The source explicitly separates the two ratings and ties the continuous one to thermal survival, so the substitution silently swaps a thermal limit for a burst limit.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Falls back from max_power_w to max_continuous_power_w with `or`, comparing a CONTINUOUS rating against a PEAK requirement whenever the burst figure is missing — a silent substitution of two different physical ratings with no warning (ADR 0020). Also compares against motor_peak_shaft_w, which is cell-count-independent, so the flag is identical for every row in the table.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `docstring: "``motor_shaft_peak_w`` is the required mechanical shaft power (P_aero / η_prop), not the aerodynamic power.  Motor catalog ratings (max_power_w) are shaft-power ratings, so the comparison is apples-to-apples."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
