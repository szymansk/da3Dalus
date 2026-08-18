---
name: t_over_w_fl
symbol: T/W
kind: quantity
unit: dimensionless
cluster: perf-matching
user_visible: false
source_status: SOURCED
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/sourced
  - flag/anomaly
  - flag/divergence
---

# Thrust-to-weight (field length)

**Definition.** Ratio of effective thrust to weight used in the takeoff ground roll.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
t_over_w = t_mean / weight_n
```

**Inputs.**

- [[t_mean_fl|Effective mean thrust]]
- [[weight_n_fl|Aircraft weight]]

**Produced by.** `app/services/field_length_service.py:202` — `_compute_s_to_ground`

**Consumed by.**

- in this graph: `Takeoff ground roll`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `s_to_ground:203`

**Source.** 🟢 SOURCED

> Sadraey 2013 §4.3.1: thrust loading T/W is the matching-plot vertical axis; Scholz 05_PreliminarySizing §5.2 uses T_TO/(m_MTO*g).
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
T/W = T/(m*g)
```

**⚠️ Divergence from the source.** Implementation only, not methodological: no zero guard, so t_static_N = 0 raises ZeroDivisionError instead of the module's ServiceException envelope.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** No zero guard — t_static_N = 0 raises ZeroDivisionError instead of the module's ServiceException envelope (the guard at _check_thrust only tests for None).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# T/W dimensionless`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
