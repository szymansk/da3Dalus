---
name: alr-score-re-agnostic
symbol: —
kind: quantity
unit: dimensionless (0..1)
cluster: aero-polars
user_visible: true
source_status: NO_SOURCE_FOUND
---

# re_agnostic suitability score

**Definition.** Weighted, weight-renormalised sum of five normalised low-Re quality metrics, clamped to [0,1].

**Formula — as the code writes it.**

```
score = sum(v * w for v, w in components) / total_weight
return float(min(max(score, 0.0), 1.0))
```

**Inputs.** [[alr-ld-max|Section (L/D)_max]] · [[alr-cl-max|Section CL_max]] · [[alr-drag-bucket-width|Drag bucket width]] · [[alr-stall-gentleness|Stall gentleness]] · [[alr-cd-min|Section CD_min]] · [[alr-score-weights|re_agnostic component weights]] · [[alr-score-ld-ref|L/D reference for re_agnostic]] · [[alr-score-cl-max-ref|CL_max reference for re_agnostic]] · [[alr-score-bucket-ref|Drag-bucket reference for re_agnostic]] · [[alr-score-cd-min-ref|CD_min reference for re_agnostic]] · [[alr-gentleness-scale|Stall gentleness normalisation scale]]

**Produced by.** `app/services/airfoil_low_re_service.py:890` — `score_re_agnostic`

**Consumed by.**

- in this graph: [[alr-score-mission|Mission suitability score]] · [[sui-active-lens|active_lens]]
- outside it: `suitability_service:467 → SuitabilityItem.re_agnostic` · `score_mission:939` · `frontend AirfoilSuitabilityCard.tsx:382`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source consulted proposes a weighted scalar airfoil-merit index; the composite and all five references are in-repo constructions.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `score = sum(v * w for v, w in components) / total_weight
return float(min(max(score, 0.0), 1.0))`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
