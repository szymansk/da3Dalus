---
name: end_drag
symbol: D
kind: quantity
unit: N
cluster: perf-envelope
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/sourced
  - audit/confirmed
---

# Drag force

**Definition.** Total drag at the evaluation speed.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
drag = q * s_ref * cd
```

**Inputs.**

- [[end_q|Dynamic pressure (endurance)]]
- [[end_cd_total|Total drag coefficient]]

**Produced by.** `app/services/endurance_service.py:123` — `_power_required`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Aerodynamic power`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> Definitional.
>
> — via `aero`

**The source states it as.**

```
D = q*S*C_D
```

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
