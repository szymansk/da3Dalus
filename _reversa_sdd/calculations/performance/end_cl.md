---
name: end_cl
symbol: C_L(V)
kind: quantity
unit: -
cluster: perf-envelope
user_visible: false
source_status: SOURCED
---

# Level-flight lift coefficient

**Definition.** Lift coefficient required to sustain level flight at speed V.

**Formula — as the code writes it.**

```
cl = (mass * G) / (q * s_ref)
```

**Inputs.** [[end_mass|Total aircraft mass (endurance)]] · [[end_g|Gravitational acceleration (endurance)]] · [[end_q|Dynamic pressure (endurance)]]

**Produced by.** `app/services/endurance_service.py:120` — `_power_required`

**Consumed by.**

- in this graph: [[end_cd_total|Total drag coefficient]]

**Source.** 🟢 SOURCED

> Level-flight equilibrium L = W with L = q*S*C_L; Anderson, Introduction to Flight, Ch. 6.
>
> — via `aero`

**The source states it as.**

```
C_L = W/(q*S)
```

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
