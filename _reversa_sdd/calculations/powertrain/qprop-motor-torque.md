---
name: qprop-motor-torque
symbol: Q_motor
kind: quantity
unit: Nm
cluster: powertrain
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/sourced
  - audit/confirmed
  - flag/divergence
---

# Motor-produced torque

**Definition.** Shaft torque produced by the motor at a given current, net of the no-load current.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
q_motor = (i - i0) / kv_si
```

**Inputs.**

- [[qprop-current-for-rpm|Terminal current at a candidate RPM]]
- [[motor-io-input|No-load current]]  — *⤵ fallback*
- [[motor-kv-si|Motor speed constant in SI]]

**Produced by.** `app/services/powertrain_performance.py:535` — `solve_qprop_operating_point.residual`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Torque-balance residual`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:537`

**Source.** 🟢 SOURCED

> Drela, 'DC Motor / Propeller Matching', §1.1: Q_m = (I - i_0)/K_Q, where i_0 is the zero-torque (friction/windage) current and K_Q the torque constant; by energy conservation in the ideal case K_Q = K_v.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
Q_m = (I - i_0) / K_Q,  with K_Q = K_v in the ideal case
```

**⚠️ Divergence from the source.** Drela distinguishes K_Q from K_v and notes 'measured K_Q often differs slightly from K_v ... Allowing this discrepancy improves efficiency predictions near the maximum-efficiency point.' The code hardwires K_Q = Kv_si with no separate torque constant, adopting the idealisation the source flags as a known accuracy limit.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `docstring: "motor torque:       Q_motor(I) = (I − I0) / Kv_si"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
