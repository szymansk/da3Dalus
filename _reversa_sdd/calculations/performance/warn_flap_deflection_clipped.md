---
name: warn_flap_deflection_clipped
kind: quantity
unit: dimensionless
cluster: perf-oppoints
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: derived
tags:
  - cluster/perf-oppoints
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - flag/divergence
---

# FLAP_DEFLECTION_CLIPPED warning

**Definition.** Audit-trail warning appended when the flap target exceeded the TED limit.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
warnings.append("FLAP_DEFLECTION_CLIPPED")
```

**Inputs.**

- [[flap_deflection_clipped_value|Clipped flap deflection]]  — *⊣ limit*

**Produced by.** `app/services/operating_point_generator_service.py:105` — `_clip_flap_to_ted_limit`

**Consumed by.**

- outside it: `app/models/analysismodels.py:28 (warnings JSON)` · `frontend/components/workbench/OperatingPointsPanel.tsx:483-488`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Warning-emission policy is app-internal (ADR 0020). No external source applies.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
