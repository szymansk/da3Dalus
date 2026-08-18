---
name: weight-n
symbol: W
kind: quantity
unit: N
cluster: aero-spanwise
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/sourced
  - audit/confirmed
---

# Weight

**Definition.** Weight of the curve's mass.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
weight_n = m * g
```

**Inputs.**

- [[mass-set|Speed-polar mass set]]
- [[gravity-g|Gravitational acceleration]]

**Produced by.** `app/services/analysis_service.py:513` — `_compute_speed_polar`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Glide forward speed` · `Stall speed`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> Scholz 05_PreliminarySizing §5.6.2 Eq. 5.30; Sadraey §4.3.2 Eq. 4.30
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
L = m_MTO · g
```

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
