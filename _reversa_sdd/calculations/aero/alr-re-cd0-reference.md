---
name: alr-re-cd0-reference
symbol: cd0_ref
kind: quantity
unit: dimensionless
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Per-Re fleet cd0 reference

**Definition.** 20th-percentile cd0 across all airfoils interpolated to the query Re.

**Formula — as the code writes it.**

```
cd0_arr = np.array(cd0_values, dtype=float)
return float(np.percentile(cd0_arr, percentile))
```

**Inputs.** [[alr-polar-cd0|Airfoil cd0 (parabolic fit vertex)]] · [[alr-cd0-reference-percentile|Fleet cd0 reference percentile]]

**Produced by.** `app/services/airfoil_low_re_service.py:823` — `compute_re_cd0_reference`

**Consumed by.**

- in this graph: [[alr-efficiency|Efficiency component of score_target_cl]]
- outside it: `suitability_service:412,415,420,425` · `score_target_cl:1081`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source for benchmarking a section against a fleet percentile rather than an absolute target. Consequence: the score is not a property of the airfoil — importing or deleting airfoils changes every other airfoil's Efficiency at the same query.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Score depends on the DB population: adding or removing airfoils changes every other airfoil's efficiency score for the same query.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `cd0_arr = np.array(cd0_values, dtype=float)
return float(np.percentile(cd0_arr, percentile))`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
