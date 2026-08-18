---
name: qprop-back-emf-floor
symbol: back_emf_floor
kind: quantity
unit: V
cluster: powertrain
user_visible: false
source_status: SOURCED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/sourced
---

# Back-EMF floor at the current ceiling

**Definition.** Back-EMF remaining when the motor draws exactly the maximum allowed current — sets the lowest RPM the solver will consider.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
back_emf_floor = V_terminal - max_current_a * rm
```

**Inputs.**

- [[curve-v-terminal|Motor terminal voltage]]
- [[motor-max-current-input|Motor burst current limit]]  — *⊣ limit*
- [[motor-rm-ohm-input|Winding resistance]]

**Produced by.** `app/services/powertrain_performance.py:548` — `solve_qprop_operating_point`

**Consumed by.**

- in this graph: `RPM at the current ceiling`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:549`

**Source.** 🟢 SOURCED

> Drela, 'DC Motor / Propeller Matching', §1.1: V = i R + Omega/Kv — evaluated at the current ceiling i = I_max, the remaining back-EMF is V - I_max*R.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
v_m = V - i R,  at i = I_max
```

**Cited in the code itself.** `# back_emf = V_terminal − max_current_a·rm ; rpm = back_emf·kv_si·60/2π`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
