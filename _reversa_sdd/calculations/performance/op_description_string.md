---
name: op_description_string
kind: quantity
unit: dimensionless
cluster: perf-oppoints
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Operating-point description

**Definition.** Human-readable summary of the point's configuration, load factor, speed and altitude.

**Formula — as the code writes it.**

```
f"config={target['config']}, target_n={target.get('n_target', 1.0):.2f}, V={velocity:.2f}mps, altitude={altitude:.1f}m"
```

**Inputs.** [[turn_n_target|Turn target load factor]] · [[default_altitude_m|Default environment altitude]]

**Produced by.** `app/services/operating_point_generator_service.py:983` — `_trim_or_estimate_point`

**Consumed by.**

- outside it: `app/models/analysismodels.py (description)` · `frontend/components/workbench/OperatingPointsPanel.tsx`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Presentation string. No engineering source applies.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
