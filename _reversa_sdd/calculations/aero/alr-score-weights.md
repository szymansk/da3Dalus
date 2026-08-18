---
name: alr-score-weights
symbol: w_i
kind: parameter
unit: dimensionless
cluster: aero-polars
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-parameter
tags:
  - cluster/aero-polars
  - class/unclassified-parameter
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# re_agnostic component weights

**Definition.** Relative weights of the five re_agnostic score components.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `ld 0.35, cl_max 0.25, bucket 0.20, stall 0.10, cd_min 0.10`

**Formula — as the code writes it.**

```
components.append((min(ld_max / LD_REF, 1.0), 0.35)) ... (min(cl_max / CL_MAX_REF, 1.0), 0.25) ... (min(bucket / BUCKET_REF, 1.0), 0.20) ... (gentleness_score, 0.10) ... (cd_score, 0.10)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:863` — `score_re_agnostic`

**Consumed by.**

- in this graph: `re_agnostic suitability score`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `score_re_agnostic:890`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source for 0.35/0.25/0.20/0.10/0.10. Renormalising by the weights actually present means an airfoil missing its worst metric is scored on the remainder and can outrank a complete one — a defect, not a weighting choice.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Weights are renormalised by the weights actually present, so an airfoil missing its worst metric is scored on the remainder and can outrank a complete one.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `score = sum(v * w for v, w in components) / total_weight`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
