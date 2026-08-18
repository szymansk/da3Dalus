---
name: turn_bank_angles
symbol: φ
kind: constant
unit: deg
cluster: perf-oppoints
user_visible: true
source_status: PARTIAL
node_class: unclassified-constant
tags:
  - cluster/perf-oppoints
  - class/unclassified-constant
  - source/partial
  - surface/user-visible
  - flag/divergence
---

# Default turn bank angles

**Definition.** Bank angles for which default turn operating points are generated.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `20, 40, 60`

**Formula — as the code writes it.**

```
for bank in (20, 40, 60)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:499` — `_build_target_definitions`

**Consumed by.**

- in this graph: `Turn target load factor`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/operating_point_generator_service.py:491-497 (turn_<bank> targets)`

**Source.** 🟡 PARTIAL

> Sadraey §12.3.3, Table 12.5 — Class I (small light aircraft), Phase A Level 1 benchmark bank angle is 60°; Phase B 45°, Phase C 30°
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** 60° is a genuine benchmark in the source (and the classic n = 2 steep turn). 20° and 40° are not: the source's other benchmark banks are 45° and 30°. If the set were meant to follow Sadraey Table 12.5 it should be (30, 45, 60).

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
