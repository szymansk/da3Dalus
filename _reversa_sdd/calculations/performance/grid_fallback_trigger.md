---
name: grid_fallback_trigger
kind: constant
unit: dimensionless
cluster: perf-oppoints
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/perf-oppoints
  - class/unclassified-constant
  - source/no-source-found
  - flag/divergence
---

# Grid-fallback trigger threshold

**Definition.** Score above which the grid search runs after the Opti solve.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.35`

**Formula — as the code writes it.**

```
if best_score > 0.35:
```

**Inputs.**

- [[trim_score|Trim score]]

**Produced by.** `app/services/operating_point_generator_service.py:935` — `_trim_or_estimate_point`

**Consumed by.**

- in this graph: `Trim solver path label`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/operating_point_generator_service.py:936-956`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Same unsourced 0.35 as trim_status_threshold, duplicated rather than shared. Coupling them means any retune of the reporting threshold silently retunes the solver's fallback behaviour.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `gh-528 / epic gh-525 finding C3: grid-search fallback updates BOTH alpha AND velocity post-trim.`

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
