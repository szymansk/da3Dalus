---
name: alr-family-bonus
symbol: —
kind: constant
unit: dimensionless
cluster: aero-polars
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Mission family bonus

**Definition.** Multiplier applied when the airfoil family is / is not in the mission's preferred list.

**Value.** `1.0 / 0.7`

**Formula — as the code writes it.**

```
family_bonus = 1.0 if family in preferred_families else 0.7
```

**Inputs.** [[alr-family|Airfoil family label]] · [[low-re-mission-weights|Mission weighting table]]

**Produced by.** `app/services/airfoil_low_re_service.py:918` — `score_mission`

**Consumed by.**

- in this graph: [[alr-score-mission|Mission suitability score]]
- outside it: `score_mission:939`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** The family↔mission pairings are sourced (see low-re-mission-weights) but the 0.7 penalty magnitude is a bare constant with no source.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Magic 0.7 penalty, no source.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Family bonus: 1.0 if preferred, 0.7 if not
family_bonus = 1.0 if family in preferred_families else 0.7`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
