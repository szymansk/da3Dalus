---
name: v_stall_turn
symbol: V_stall_turn
kind: quantity
unit: m/s
cluster: perf-oppoints
user_visible: true
source_status: SOURCED
---

# Stall speed in the turn

**Definition.** Clean stall speed scaled by the square root of the turn load factor.

**Formula — as the code writes it.**

```
v_stall_turn = vs_clean * (n**0.5)
```

**Inputs.** [[vs_clean|Clean stall speed reference]] · [[turn_load_factor_n|Turn load factor]]

**Produced by.** `app/services/operating_point_generator_service.py:170` — `_apply_turn_feasibility`

**Consumed by.**

- in this graph: [[warn_stall_in_turn|STALL_IN_TURN warning + LIMIT_REACHED]]
- outside it: `app/services/operating_point_generator_service.py:171-178 (STALL_IN_TURN)`

**Source.** 🟢 SOURCED

> Lennon, Basics of R/C Model Aircraft Design (1996), Ch. 21 / Ch. 4 — in a turn the demanded lift coefficient rises in proportion to n ('increases 11.8 times to CL 0.85'); if it exceeds CL_max an accelerated (high-speed) stall results. Combined with Sadraey §4.3.2, Eq. 4.30 (W = ½ρV_s²S·CL_max).
>
> — via `rc-aircraft-designer, aircraft-design-scholz`

**The source states it as.**

```
nW = ½ρV²S·CL_max with W = ½ρV_s²S·CL_max  ⇒  V_s,turn = V_s·sqrt(n)
```

**⚠️ Divergence from the source.** Exact algebraic equivalent of the sources. Correct.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
