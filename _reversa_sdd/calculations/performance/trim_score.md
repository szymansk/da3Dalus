---
name: trim_score
symbol: score
kind: quantity
unit: dimensionless
cluster: perf-oppoints
user_visible: true
source_status: NOT_ASSESSED
---

# Trim score

**Definition.** Scalar trim-quality residual: pitch moment plus weighted side force and CL error.

**Formula — as the code writes it.**

```
score = abs(cm) + 0.5 * abs(cy); if cl_target is not None: score += 0.3 * abs(cl - cl_target)
```

**Inputs.** [[cl_target|Target lift coefficient]]

**Produced by.** `app/services/operating_point_generator_service.py:193` — `_compute_trim_score`

**Consumed by.**

- in this graph: [[grid_fallback_trigger|Grid-fallback trigger threshold]] · [[trim_residuals|Trim residual record]] · [[trim_status_threshold|Trim acceptance threshold]]
- outside it: `app/services/operating_point_generator_service.py:854 (status threshold)` · `app/services/operating_point_generator_service.py:935 (grid-fallback trigger)` · `app/services/trim_enrichment_service.py:451-461` · `app/services/add_turn_service.py:101`

**Source.** ⚪ not assessed


**⚠️ Anomaly.** Weights 1 / 0.5 / 0.3 are magic numbers with no cited source, and they disagree with the Opti objective's 50 / 3 / 15 weighting of the same three residuals.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
