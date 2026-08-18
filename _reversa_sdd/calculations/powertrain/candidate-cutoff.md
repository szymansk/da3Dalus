---
name: candidate-cutoff
symbol: 10
kind: constant
unit: count
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/powertrain
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Recommendation list cut-off

**Definition.** Number of highest-confidence candidates returned to the client.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `10`

**Formula — as the code writes it.**

```
return PowertrainSizingResponse(recommendations=candidates[:10], warnings=warnings)
```

**Inputs.**

- [[combo-confidence|Combo confidence]]

**Produced by.** `app/services/powertrain_sizing_service.py:318` — `size_powertrain`

**Consumed by.**

- outside it: `app/api/v2/endpoints/aeroplane/powertrain_sizing.py:62`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Presentation parameter, no engineering content.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Magic number, not configurable. Combined with the confidence cap at 1.0 (line 125), every combo that beats the target ties, so which 10 survive depends on DB iteration order.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
