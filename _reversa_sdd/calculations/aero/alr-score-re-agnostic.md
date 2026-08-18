---
name: alr-score-re-agnostic
symbol: —
kind: quantity
unit: dimensionless (0..1)
cluster: aero-polars
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# re_agnostic suitability score

**Definition.** Weighted, weight-renormalised sum of five normalised low-Re quality metrics, clamped to [0,1].

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
score = sum(v * w for v, w in components) / total_weight
return float(min(max(score, 0.0), 1.0))
```

**Inputs.**

- [[alr-ld-max|Section (L/D)_max]]  — *⊣ limit*
- [[alr-cl-max|Section CL_max]]  — *⊣ limit*
- [[alr-drag-bucket-width|Drag bucket width]]
- [[alr-stall-gentleness|Stall gentleness]]  — *⊣ limit*
- [[alr-cd-min|Section CD_min]]  — *⊣ limit*
- [[alr-score-weights|re_agnostic component weights]]
- [[alr-score-ld-ref|L/D reference for re_agnostic]]
- [[alr-score-cl-max-ref|CL_max reference for re_agnostic]]  — *⊣ limit*
- [[alr-score-bucket-ref|Drag-bucket reference for re_agnostic]]
- [[alr-score-cd-min-ref|CD_min reference for re_agnostic]]  — *⊣ limit*
- [[alr-gentleness-scale|Stall gentleness normalisation scale]]

**Produced by.** `app/services/airfoil_low_re_service.py:890` — `score_re_agnostic`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Mission suitability score` · `active_lens`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
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
