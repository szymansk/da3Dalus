---
name: alr-efficiency
symbol: Efficiency
kind: quantity
unit: dimensionless (0..1)
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Efficiency component of score_target_cl

**Definition.** How clean the airfoil is relative to the fleet cd0 reference at the same Re, capped at 1.

**Formula — as the code writes it.**

```
efficiency = min(re_cd0_reference / cd0, 1.0)
```

**Inputs.** [[alr-re-cd0-reference|Per-Re fleet cd0 reference]] · [[alr-polar-cd0|Airfoil cd0 (parabolic fit vertex)]]

**Produced by.** `app/services/airfoil_low_re_service.py:1081` — `score_target_cl`

**Consumed by.**

- in this graph: [[alr-score-target-cl|target-CL suitability score]]
- outside it: `score_target_cl:1085`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Ratio to a fleet percentile; inherits alr-re-cd0-reference's population dependence. No source.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `if re_cd0_reference > 0.0 and cd0 > 0.0:
    efficiency = min(re_cd0_reference / cd0, 1.0)
else:
    efficiency = 1.0`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
