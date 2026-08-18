---
name: end_battery_mass_predicted
symbol: m_bat,pred
kind: quantity
unit: g
cluster: perf-envelope
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Capacity-implied battery mass

**Definition.** Battery mass implied by capacity and pack specific energy.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
predicted_kg = capacity_wh / specific_energy_wh_per_kg; predicted_g = predicted_kg * 1000.0
```

**Inputs.**

- [[end_capacity_wh|Battery capacity]]
- [[end_specific_energy|Default pack specific energy]]  — *⤵ fallback*

**Produced by.** `app/services/endurance_service.py:185` — `_check_battery_mass_consistency`

**Consumed by.**

- in this graph: `Battery-mass deviation`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `metricsAdapters.toPowertrainItems detail.batteryMassPredicted` · `GET /aeroplanes/{id}/endurance`

**Source.** 🟡 PARTIAL

> Definitional; E* inherits end_specific_energy (Hepperle 2012 vs RC-Network 153 Wh/kg).
>
> — via `rc`

**The source states it as.**

```
m_bat = E_batt / E*
```

**⚠️ Divergence from the source.** Unguarded division: specific_energy_wh_per_kg comes straight from a user-editable design assumption with no > 0 check, so setting it to 0 raises ZeroDivisionError -> HTTP 500 (endurance.py:50). A user-editable field must not be able to 500 the endpoint.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Unguarded division: specific_energy_wh_per_kg comes straight from a user-editable design assumption with no >0 check, so setting it to 0 raises ZeroDivisionError, which the endpoint converts to a 500 (endurance.py:50). Also computed before the missing-input early-return, so it is the one number returned even in the degenerate path — no, it is not: the early return at line 321 sets it to None while the value was never computed. Not surfaced in EnduranceCard, only in the metrics dashboard detail panel.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
