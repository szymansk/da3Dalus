---
name: alr-score-target-cl
symbol: —
kind: quantity
unit: dimensionless (0..1)
cluster: aero-polars
user_visible: true
source_status: NO_SOURCE_FOUND
---

# target-CL suitability score

**Definition.** Product of Match and Efficiency at a given operating CL, clamped to [0,1].

**Formula — as the code writes it.**

```
score = match * efficiency
return float(min(max(score, 0.0), 1.0))
```

**Inputs.** [[alr-match|Match component of score_target_cl]] · [[alr-efficiency|Efficiency component of score_target_cl]]

**Produced by.** `app/services/airfoil_low_re_service.py:1085` — `score_target_cl`

**Consumed by.**

- in this graph: [[sui-active-lens|active_lens]]
- outside it: `suitability_service:487,496,505 → SuitabilityItem.target_cl_cruise / target_cl_best_glide / target_cl_min_sink` · `suitability_service:632 (ranking)` · `frontend AirfoilSuitabilityCard.tsx:387`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Product of two unsourced components; no source proposes this composition.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `score = match * efficiency
return float(min(max(score, 0.0), 1.0))`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
