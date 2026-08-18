---
name: fe_gust_critical_neg
symbol: n_gust < -0.4 n_lim
kind: quantity
unit: -
cluster: perf-envelope
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/partial
  - surface/user-visible
---

# Negative gust-critical trigger

**Definition.** First speed at which the down-gust load factor exceeds the negative maneuver limit.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if n_neg < -0.4 * g_limit and not warned_negative: ...
```

**Inputs.**

- [[fe_gust_n_neg|Negative gust load factor]]
- [[fe_g_limit|Structural limit load factor]]  — *⤵ fallback*
- [[fe_neg_g_factor|Negative g-limit ratio]]  — *⊣ limit*

**Produced by.** `app/services/flight_envelope_service.py:260` — `_build_gust_lines`

**Consumed by.**

- outside it: `VnDiagram.tsx criticalWarnings banner`

**Source.** 🟡 PARTIAL

> Criterion standard; the -0.4 threshold inherits fe_neg_g_factor (Sadraey §10.4.1 / FAR 23.337(b)(1), transport/GA basis).
>
> — via `scholz`

**The source states it as.**

```
gust-critical when n_gust < -0.4*n_lim
```

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
