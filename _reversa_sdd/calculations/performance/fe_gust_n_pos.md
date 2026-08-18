---
name: fe_gust_n_pos
symbol: n_gust+
kind: quantity
unit: g
cluster: perf-envelope
user_visible: true
source_status: SOURCED
---

# Positive gust load factor

**Definition.** Load factor reached by an up-gust at each sweep speed.

**Formula — as the code writes it.**

```
n_pos = 1.0 + delta_n
```

**Inputs.** [[fe_delta_n|Gust load-factor increment]]

**Produced by.** `app/services/flight_envelope_service.py:240` — `_build_gust_lines`

**Consumed by.**

- in this graph: [[fe_gust_critical_pos|Positive gust-critical trigger]]
- outside it: `VnDiagram.tsx gust_lines_positive`

**Source.** 🟢 SOURCED

> FAR 25.341(a) / CS-VLA 341 gust-envelope construction.
>
> — via `scholz`

**The source states it as.**

```
n = 1 + delta_n
```

**⚠️ Scale (ADR 0023).** Inherits the RC kinematic breakdown described under gust_u_vc — the value is a linear extrapolation past stall.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
