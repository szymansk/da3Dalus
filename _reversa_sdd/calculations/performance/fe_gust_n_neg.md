---
name: fe_gust_n_neg
symbol: n_gust-
kind: quantity
unit: g
cluster: perf-envelope
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/scale
---

# Negative gust load factor

**Definition.** Load factor reached by a down-gust at each sweep speed.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
n_neg = 1.0 - delta_n
```

**Inputs.**

- [[fe_delta_n|Gust load-factor increment]]

**Produced by.** `app/services/flight_envelope_service.py:241` — `_build_gust_lines`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Negative gust-critical trigger`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
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
