---
name: warn_stale_no_polar
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

# STALE_NO_POLAR warning

**Definition.** Warning stamped on every target when reference speeds are cold-start estimates.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if refs.get("provenance") != "cold_start": return targets ... warnings.append("STALE_NO_POLAR")
```

**Inputs.**

- [[refs_provenance|Reference-speed provenance]]

**Produced by.** `app/services/operating_point_generator_service.py:386` — `_stamp_stale_no_polar`

**Consumed by.**

- outside it: `app/models/analysismodels.py:28 (warnings)` · `frontend/components/workbench/OperatingPointsPanel.tsx:483-488`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** App warning policy (ADR 0020). No external source applies.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `The warning rides through to the persisted ``OperatingPointModel.warnings`` so consumers (UI chip row, AVL replay, SonarQube enrichment) can flag these OPs as estimated rather than physics-derived (gh-535 / epic gh-525 M1 follow-up).`

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
