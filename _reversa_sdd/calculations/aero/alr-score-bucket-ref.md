---
name: alr-score-bucket-ref
symbol: —
kind: constant
unit: dimensionless (ΔCL)
cluster: aero-polars
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Drag-bucket reference for re_agnostic

**Definition.** Bucket width that maps to a full 1.0 on the bucket component.

**Value.** `0.8`

**Formula — as the code writes it.**

```
BUCKET_REF = 0.8  # wide drag bucket
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:857` — `score_re_agnostic`

**Consumed by.**

- in this graph: [[alr-score-re-agnostic|re_agnostic suitability score]]
- outside it: `score_re_agnostic:869`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source for 0.8, and it directly contradicts settings.low_re_bucket_tolerance_ref = 0.6 used by score_target_cl — two different 'wide drag bucket' references inside one module (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Conflicts with settings.low_re_bucket_tolerance_ref = 0.6 (app/settings.py:104), the reference bucket width used by score_target_cl — two different 'wide bucket' references.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `BUCKET_REF = 0.8  # wide drag bucket`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
