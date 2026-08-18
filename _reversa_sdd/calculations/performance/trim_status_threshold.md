---
name: trim_status_threshold
kind: constant
unit: dimensionless
cluster: perf-oppoints
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/perf-oppoints
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Trim acceptance threshold

**Definition.** Trim score below which an operating point is declared TRIMMED.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.35`

**Formula — as the code writes it.**

```
trim_status = (OperatingPointStatus.TRIMMED if best_score < 0.35 else OperatingPointStatus.NOT_TRIMMED)
```

**Inputs.**

- [[trim_score|Trim score]]

**Produced by.** `app/services/operating_point_generator_service.py:854` — `_apply_limit_warnings`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/models/analysismodels.py (status)` · `frontend/components/workbench/OperatingPointsPanel.tsx (status column)` · `app/services/trim_enrichment_service.py:451-461`

**Source.** 🔴 NO SOURCE FOUND

> Defining authority: Sadraey §12.5 — the trim condition is ΣM_cg = 0, i.e. Cm = 0
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 0.35 has no source and is not a small number. Because the score is \|Cm\| + 0.5\|CY\| + 0.3\|ΔCL\|, a point with \|Cm\| = 0.34 and everything else perfect is reported TRIMMED — for a typical RC wing that residual pitching moment is of the same order as the whole tail's trim contribution. The threshold is also duplicated at line 935 as the grid-fallback trigger, so 'good enough to report' and 'good enough to stop searching' are the same number by accident rather than by design.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Magic threshold with no cited source, duplicated at line 935 as the grid-fallback trigger; \|Cm\| = 0.34 is a very large residual pitching moment yet still reports TRIMMED.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
