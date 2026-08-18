---
name: qprop-torque
symbol: Q
kind: quantity
unit: Nm
cluster: powertrain
user_visible: false
source_status: SOURCED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/sourced
  - flag/anomaly
---

# Solved shaft torque

**Definition.** Shaft torque at the solved operating point.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
torque = max((current - i0) / kv_si, 0.0)
```

**Inputs.**

- [[qprop-current|Solved terminal current]]  — *⊣ limit*
- [[motor-io-input|No-load current]]  — *⤵ fallback*
- [[motor-kv-si|Motor speed constant in SI]]

**Produced by.** `app/services/powertrain_performance.py:580` — `solve_qprop_operating_point`

**Consumed by.**

- in this graph: `Solved shaft power (QPROP)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:581` · `app/services/powertrain_performance.py:590`

**Source.** 🟢 SOURCED

> Drela, 'DC Motor / Propeller Matching', §1.1: Q_m = (I - i_0)/K_Q, with K_Q = K_v in the ideal case.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
Q_m = (I - i_0) / K_Q
```

**⚠️ Anomaly.** Same as qprop-current: present on the dataclass, dropped before the API response.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `docstring: "shaft torque Q = (I − Io)/Kv"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
