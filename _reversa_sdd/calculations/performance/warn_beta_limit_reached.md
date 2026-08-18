---
name: warn_beta_limit_reached
kind: quantity
unit: dimensionless
cluster: perf-oppoints
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-oppoints
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# BETA_LIMIT_REACHED warning

**Definition.** Status downgrade when the solved sideslip exceeds the profile's beta limit.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if max_beta is not None and abs(best_beta) > float(max_beta): trim_status = OperatingPointStatus.LIMIT_REACHED; warnings.append("BETA_LIMIT_REACHED")
```

**Inputs.**

- [[beta_trimmed|Trimmed sideslip angle]]
- [[default_max_beta_deg|Default maximum sideslip]]  — *⤵ fallback*

**Produced by.** `app/services/operating_point_generator_service.py:865` — `_apply_limit_warnings`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/models/analysismodels.py:28` · `frontend/components/workbench/OperatingPointsPanel.tsx:483-488`

**Source.** 🟡 PARTIAL

> Sadraey §12.3.3 — control power must develop at least 10° sideslip in the power approach; FAR 25.147 — ±15° heading change
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** A sideslip limit is a real design constraint in the source. With the default max_beta = 30° (3× the largest cited requirement) the check is inert. Symmetric abs() is appropriate here, unlike the alpha case.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
