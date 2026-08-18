---
name: fe_gust_n_neg
symbol: n_gust-
kind: quantity
unit: g
cluster: perf-envelope
user_visible: true
source_status: SOURCED
---

# Negative gust load factor

**Definition.** Load factor reached by a down-gust at each sweep speed.

**Formula — as the code writes it.**

```
n_neg = 1.0 - delta_n
```

**Inputs.** [[fe_delta_n|Gust load-factor increment]]

**Produced by.** `app/services/flight_envelope_service.py:241` — `_build_gust_lines`

**Consumed by.**

- in this graph: [[fe_gust_critical_neg|Negative gust-critical trigger]]
- outside it: `VnDiagram.tsx gust_lines_negative`

**Source.** 🟢 SOURCED

> FAR 25.341(a) / CS-VLA 341.
>
> — via `scholz`

**The source states it as.**

```
n = 1 - delta_n
```

**⚠️ Scale (ADR 0023).** Same as fe_gust_n_pos.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
