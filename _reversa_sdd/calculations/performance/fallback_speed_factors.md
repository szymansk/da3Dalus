---
name: fallback_speed_factors
kind: constant
unit: dimensionless
cluster: perf-oppoints
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Grid-search velocity factors

**Definition.** Velocity multipliers swept by the grid-search fallback.

**Value.** `[1.0, 0.95, 0.90, 0.85] / [1.0, 1.05, 1.10, 1.15]; floor 2.0 m/s`

**Formula — as the code writes it.**

```
if name == "max_level_speed": factors = [1.0, 0.95, 0.90, 0.85] else: factors = [1.0, 1.05, 1.10, 1.15]; return [max(2.0, base_velocity * f) for f in factors]
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:514` — `_fallback_speeds`

**Consumed by.**

- in this graph: [[trim_residuals|Trim residual record]]
- outside it: `app/services/operating_point_generator_service.py:818 (_grid_search_trim)`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** [1.0, 0.95, 0.90, 0.85] / [1.0, 1.05, 1.10, 1.15] and the 2.0 m/s floor have no source. Consequence: when the grid path wins, the stored operating-point velocity differs from the requested target by up to ±15 % with no warning, so a point labelled 'cruise' can be a 15 %-off-cruise solution.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** When the grid path wins, the OP's stored velocity is silently changed by up to ±15 % from the requested target with no warning (only recorded inside trim_residuals).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
