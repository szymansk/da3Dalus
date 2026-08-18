---
name: combo-confidence
symbol: confidence
kind: quantity
unit: dimensionless (0..1)
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Combo confidence

**Definition.** How well a motor+battery combo meets the flight-time target: the achieved/target ratio capped at 1.0.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if target_flight_time_min <= 0: return 0.0 ; return min(flight_time_min / target_flight_time_min, 1.0)
```

**Inputs.**

- [[combo-flight-time-min|Estimated flight time]]  — *⊣ limit*

**Produced by.** `app/services/powertrain_sizing_service.py:125` — `_compute_confidence`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Recommendation list cut-off`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_sizing_service.py:271` · `app/services/powertrain_sizing_service.py:317`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source defines a 'confidence' metric for a powertrain combination. The quantity computed is target attainment (achieved/target flight time, capped at 1.0), which is a different concept from confidence in the estimate.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Named "confidence" but measures target attainment, not uncertainty — a combo built entirely on defaulted aero (cd0/e/AR/S all guessed) can score 1.0. Name contradicts the definition. It is also the sole sort key (line 317), so every combo that beats the target ties at exactly 1.0 and the top-10 cut becomes arbitrary.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `docstring: "Smoothly scales with achieved/target ratio: meeting the target → 1.0, falling linearly toward 0 as flight time drops. No discontinuity (gh-992: the old /1.5 scaling capped an on-target combo at 0.667 and had a 3.3x cliff at 50% of target)."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
