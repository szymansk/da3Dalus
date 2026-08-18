---
name: end_p_margin_comfortable
symbol: p_margin,comf
kind: constant
unit: -
cluster: perf-envelope
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Comfortable power-margin threshold

**Definition.** Power margin above which the propulsion system is classified 'comfortable'.

**Value.** `0.20`

**Formula — as the code writes it.**

```
P_MARGIN_COMFORTABLE = 0.20  # > 20% → comfortable
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/endurance_service.py:64` — `P_MARGIN_COMFORTABLE`

**Consumed by.**

- in this graph: [[end_p_margin_class|Power-margin classification]]

**Source.** 🔴 NO SOURCE FOUND

> No source for the 20% threshold or the three-way classification. The in-code comments restate the thresholds rather than justify them.
>
> — via `rc`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**Cited in the code itself.** `"# > 20% → comfortable / # > 0% but ≤ 20% → feasible but tight / # ≤ 0% → infeasible" — thresholds asserted, NO_SOURCE_FOUND`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
