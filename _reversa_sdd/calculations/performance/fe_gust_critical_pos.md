---
name: fe_gust_critical_pos
symbol: n_gust > n_lim
kind: quantity
unit: -
cluster: perf-envelope
user_visible: true
source_status: SOURCED
---

# Positive gust-critical trigger

**Definition.** First speed at which the up-gust load factor exceeds the maneuver g-limit.

**Formula — as the code writes it.**

```
if n_pos > g_limit and not warned_positive: ...
```

**Inputs.** [[fe_gust_n_pos|Positive gust load factor]] · [[fe_g_limit|Structural limit load factor]]

**Produced by.** `app/services/flight_envelope_service.py:246` — `_build_gust_lines`

**Consumed by.**

- outside it: `VnDiagram.tsx criticalWarnings banner`

**Source.** 🟢 SOURCED

> Standard design criterion — where the gust envelope encloses the manoeuvre envelope, gust loads size the structure (FAR/CS 23.333(c), 25.341).
>
> — via `scholz`

**The source states it as.**

```
gust-critical when n_gust > n_lim
```

**⚠️ Scale (ADR 0023).** The criterion is right; the trigger fires on an unphysical delta_n at RC scale, so it will report 'structure must be sized by gust loads' far more often than reality warrants.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
