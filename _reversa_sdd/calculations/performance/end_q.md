---
name: end_q
symbol: q
kind: quantity
unit: Pa
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

# Dynamic pressure (endurance)

**Definition.** Free-stream dynamic pressure at the evaluation speed.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
q = 0.5 * rho * v * v
```

**Inputs.**

- [[end_rho|Sea-level air density]]

**Produced by.** `app/services/endurance_service.py:119` — `_power_required`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Level-flight lift coefficient` · `Drag force`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e §1.5.
>
> — via `aero`

**The source states it as.**

```
q = 0.5*rho*V^2
```

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
