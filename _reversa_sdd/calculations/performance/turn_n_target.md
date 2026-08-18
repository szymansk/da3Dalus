---
name: turn_n_target
symbol: n
kind: quantity
unit: g
cluster: perf-oppoints
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/perf-oppoints
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Turn target load factor

**Definition.** Target load factor of each default turn point.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
"n_target": round(1.0 / math.cos(math.radians(bank)), 4)
```

**Inputs.**

- [[turn_bank_angles|Default turn bank angles]]  — *⤵ fallback*

**Produced by.** `app/services/operating_point_generator_service.py:497` — `_build_target_definitions`

**Consumed by.**

- in this graph: `Target lift coefficient` · `Operating-point description`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/operating_point_generator_service.py:886 (n_target)` · `app/services/operating_point_generator_service.py:794-797 (cl_target)` · `app/services/operating_point_generator_service.py:984 (description)`

**Source.** 🟢 SOURCED

> Lennon, Basics of R/C Model Aircraft Design (1996), Ch. 21 — level-turn load factor as the vector sum of weight and centrifugal force (45° bank ⇒ 1.414 G)
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
n = 1/cos(phi)
```

**⚠️ Divergence from the source.** Form matches. The round(...,4) is arbitrary but harmless. Duplicated verbatim in add_turn_service.py:70 — two producers of one sourced formula.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Duplicated verbatim in app/services/add_turn_service.py:70 — two producers of the same formula.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
