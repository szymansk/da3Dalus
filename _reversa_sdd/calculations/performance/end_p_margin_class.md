---
name: end_p_margin_class
symbol: p_margin_class
kind: quantity
unit: -
cluster: perf-envelope
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Power-margin classification

**Definition.** Three-way verdict on propulsion adequacy from the power margin.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
margin > 0.20 -> 'comfortable'; margin > 0.0 -> 'feasible but tight'; else 'infeasible — motor underpowered'
```

**Inputs.**

- [[end_p_margin|Power margin]]
- [[end_p_margin_comfortable|Comfortable power-margin threshold]]  — *⊣ limit*

**Produced by.** `app/services/endurance_service.py:146` — `_classify_p_margin`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `EnduranceCard.tsx chip` · `metricsAdapters.toPowertrainItems`

**Source.** 🔴 NO SOURCE FOUND

> Thresholds inherit end_p_margin_comfortable (unsourced).
>
> — via `rc`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Ships a categorical verdict — 'infeasible - motor underpowered' — to the user on the strength of an unsourced threshold applied to a cruise-only margin.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
