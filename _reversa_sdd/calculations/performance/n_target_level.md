---
name: n_target_level
kind: constant
unit: g
cluster: perf-oppoints
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/perf-oppoints
  - class/unclassified-constant
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Level-flight target load factor

**Definition.** Load factor assigned to every non-turn operating point.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `1.0`

**Formula — as the code writes it.**

```
"n_target": 1.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:412` — `_build_target_definitions`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Target lift coefficient`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/operating_point_generator_service.py:886, 894`

**Source.** 🟢 SOURCED

> Sadraey §4.3.2, Eq. 4.30: in level flight L = W, i.e. n = 1 by definition

**⚠️ Divergence from the source.** Correct.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
