---
name: warn_no_control_trim_mvp
kind: constant
unit: dimensionless
cluster: perf-oppoints
user_visible: true
source_status: NO_SOURCE_FOUND
---

# NO_CONTROL_TRIM_MVP warning

**Definition.** Warning pre-stamped on the dutch-roll target.

**Value.** `NO_CONTROL_TRIM_MVP`

**Formula — as the code writes it.**

```
"warnings": ["NO_CONTROL_TRIM_MVP"]
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:508` — `_build_target_definitions`

**Consumed by.**

- outside it: `app/services/operating_point_generator_service.py:880 (warnings)` · `frontend/components/workbench/OperatingPointsPanel.tsx:483-488`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** App warning policy, no external source. It is stamped unconditionally even though lines 625-630 do allocate a yaw-control variable for this target — the warning contradicts the code.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Stamped unconditionally even though lines 625-630 do allocate a yaw-control variable for dutch_role_start, so the warning contradicts the code's actual behaviour.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
