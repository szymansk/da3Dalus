---
name: end_p_margin
symbol: p_margin
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
  - flag/anomaly
  - flag/divergence
---

# Power margin

**Definition.** Fraction of continuous motor power left unused in cruise at V_md.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
margin = (p_motor - p_req) / p_motor
```

**Inputs.**

- [[end_motor_w|Motor continuous power]]
- [[end_p_req_vmd|Power required at V_md]]

**Produced by.** `app/services/endurance_service.py:145` — `_classify_p_margin`

**Consumed by.**

- in this graph: `Power-margin classification`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `EnduranceCard.tsx` · `metricsAdapters.toPMarginGauge`

**Source.** 🟡 PARTIAL

> Arithmetic definition; no source needed for the ratio itself.
>
> — via `rc`

**The source states it as.**

```
margin = (P_motor - P_req(V_md))/P_motor
```

**⚠️ Divergence from the source.** Naming/semantics defect rather than a provenance one. Evaluated at V_md — the least demanding powered condition — yet surfaced as 'Motor reserve'. It says nothing about climb or V_max capability, which is what a reserve claim implies. Sadraey §4.3 treats rate-of-climb as the binding propulsion constraint for high-performance prop aircraft, and Lennon Ch. 21 shows RC manoeuvre loads are set by dive pull-outs, not cruise. A margin computed at best-glide cruise cannot answer either question.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Named 'power margin' but evaluated at V_md (best-glide cruise), the least demanding condition — it says nothing about climb or V_max capability, yet the UI renders it as 'Motor reserve'.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
