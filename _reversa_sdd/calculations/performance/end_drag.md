---
name: end_drag
symbol: D
kind: quantity
unit: N
cluster: perf-envelope
user_visible: false
source_status: SOURCED
---

# Drag force

**Definition.** Total drag at the evaluation speed.

**Formula — as the code writes it.**

```
drag = q * s_ref * cd
```

**Inputs.** [[end_q|Dynamic pressure (endurance)]] · [[end_cd_total|Total drag coefficient]]

**Produced by.** `app/services/endurance_service.py:123` — `_power_required`

**Consumed by.**

- in this graph: [[end_p_aero|Aerodynamic power]]

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
