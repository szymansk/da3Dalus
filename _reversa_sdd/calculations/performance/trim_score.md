---
name: trim_score
symbol: score
kind: quantity
unit: dimensionless
cluster: perf-oppoints
user_visible: true
source_status: NOT_ASSESSED
node_class: derived
tags:
  - cluster/perf-oppoints
  - class/derived
  - source/not-assessed
  - surface/user-visible
  - flag/anomaly
---

# Trim score

**Definition.** Scalar trim-quality residual: pitch moment plus weighted side force and CL error.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
score = abs(cm) + 0.5 * abs(cy); if cl_target is not None: score += 0.3 * abs(cl - cl_target)
```

**Inputs.**

- [[cl_target|Target lift coefficient]]

**Produced by.** `app/services/operating_point_generator_service.py:193` — `_compute_trim_score`

**Consumed by.**

- in this graph: `Grid-fallback trigger threshold` · `Trim residual record` · `Trim acceptance threshold`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/operating_point_generator_service.py:854 (status threshold)` · `app/services/operating_point_generator_service.py:935 (grid-fallback trigger)` · `app/services/trim_enrichment_service.py:451-461` · `app/services/add_turn_service.py:101`

**Source.** ⚪ not assessed


**⚠️ Anomaly.** Weights 1 / 0.5 / 0.3 are magic numbers with no cited source, and they disagree with the Opti objective's 50 / 3 / 15 weighting of the same three residuals.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
