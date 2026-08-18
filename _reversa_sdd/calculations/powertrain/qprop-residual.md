---
name: qprop-residual
symbol: residual
kind: quantity
unit: Nm
cluster: powertrain
user_visible: false
source_status: SOURCED
---

# Torque-balance residual

**Definition.** Difference between motor-produced and propeller-absorbed torque; its root is the operating point.

**Formula — as the code writes it.**

```
return q_motor - q_prop
```

**Inputs.** [[qprop-motor-torque|Motor-produced torque]] · [[prop-torque-demand|Propeller absorbed torque]]

**Produced by.** `app/services/powertrain_performance.py:537` — `solve_qprop_operating_point.residual`

**Consumed by.**

- in this graph: [[qprop-rpm-solution|Solved operating RPM]]
- outside it: `app/services/powertrain_performance.py:560` · `app/services/powertrain_performance.py:561` · `app/services/powertrain_performance.py:572`

**Source.** 🟢 SOURCED

> Drela, 'DC Motor / Propeller Matching', §1.1 — the operating point is where motor-produced torque equals propeller-absorbed torque; the model is described as 'the workhorse of RC electric propulsion analysis and design'.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
Q_motor(I) = Q_prop(n) at the operating point
```

**Cited in the code itself.** `docstring: "torque balance:     Q_motor(I) = Q_prop(n)        at the solution"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
