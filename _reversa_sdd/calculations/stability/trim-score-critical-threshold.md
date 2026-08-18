---
name: trim-score-critical-threshold
symbol: —
kind: constant
unit: – (dimensionless residual)
cluster: stability
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Trim divergence critical threshold

**Definition.** Trim residual score above which the trim is declared not converged and results unreliable.

**Value.** `0.5`

**Formula — as the code writes it.**

```
if trim_score > 0.5:
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/trim_enrichment_service.py:452` — `compute_enrichment`

**Consumed by.**

- outside it: `app/services/trim_enrichment_service.py:452-460`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `none — numerical, not a design quantity`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Magic threshold on a residual score whose definition and scale are set by the solvers and documented nowhere. No source applies — the underlying quantity is not a design quantity but a numerical convergence measure.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Magic threshold on a score whose definition and scale are set elsewhere (the solvers) and never documented here.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
