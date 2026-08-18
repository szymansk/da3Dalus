---
name: trim-score-warning-threshold
symbol: —
kind: constant
unit: – (dimensionless residual)
cluster: stability
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Trim quality warning threshold

**Definition.** Trim residual score above which a 'poor trim quality' warning is emitted.

**Value.** `0.1`

**Formula — as the code writes it.**

```
elif trim_score > 0.1:
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/trim_enrichment_service.py:461` — `compute_enrichment`

**Consumed by.**

- outside it: `app/services/trim_enrichment_service.py:461-469`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `none — numerical, not a design quantity`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Same as trim-score-critical-threshold: unattributed threshold on an undocumented score.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Magic threshold, no source.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
