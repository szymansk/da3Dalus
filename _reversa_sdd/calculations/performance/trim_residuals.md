---
name: trim_residuals
kind: quantity
unit: mixed (dimensionless coefficients / m/s)
cluster: perf-oppoints
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-oppoints
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Trim residual record

**Definition.** Solver diagnostics stored with the point (Opti: cm/cy/cl; grid: residual and both velocities).

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
best_residuals = dict(opti_solution.get("metrics", {}))  |  best_residuals = {"final_residual": float(gs_score), "grid_velocity_mps": float(gs_velocity), "target_velocity_mps": float(velocity)}
```

**Inputs.**

- [[trim_score|Trim score]]
- [[fallback_speed_factors|Grid-search velocity factors]]  — *⤵ fallback*

**Produced by.** `app/services/operating_point_generator_service.py:951` — `_trim_or_estimate_point`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/trim_enrichment_service.py:564` · `app/services/add_turn_service.py:102`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source applies to a diagnostics dict. Defect: the keys differ by solver path — Opti stores dimensionless coefficient residuals, the grid path stores speeds in m/s — under one dict[str, float] type, so a consumer cannot tell the units apart.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The dict carries different keys depending on the solver path (coefficients vs. speeds) under one dict[str, float] type — consumers cannot tell the units apart.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
