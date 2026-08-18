---
name: end_q
symbol: q
kind: quantity
unit: Pa
cluster: perf-envelope
user_visible: false
source_status: SOURCED
---

# Dynamic pressure (endurance)

**Definition.** Free-stream dynamic pressure at the evaluation speed.

**Formula — as the code writes it.**

```
q = 0.5 * rho * v * v
```

**Inputs.** [[end_rho|Sea-level air density]]

**Produced by.** `app/services/endurance_service.py:119` — `_power_required`

**Consumed by.**

- in this graph: [[end_cl|Level-flight lift coefficient]] · [[end_drag|Drag force]]

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
