---
name: n_target_level
kind: constant
unit: g
cluster: perf-oppoints
user_visible: true
source_status: SOURCED
---

# Level-flight target load factor

**Definition.** Load factor assigned to every non-turn operating point.

**Value.** `1.0`

**Formula — as the code writes it.**

```
"n_target": 1.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:412` — `_build_target_definitions`

**Consumed by.**

- in this graph: [[cl_target|Target lift coefficient]]
- outside it: `app/services/operating_point_generator_service.py:886, 894`

**Source.** 🟢 SOURCED

> Sadraey §4.3.2, Eq. 4.30: in level flight L = W, i.e. n = 1 by definition

**⚠️ Divergence from the source.** Correct.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
