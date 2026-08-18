---
name: qprop-back-emf
symbol: back_emf
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

# Motor back-EMF

**Definition.** Speed-proportional back-EMF at the motor terminals for a candidate RPM.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
omega = rpm * 2.0 * math.pi / 60.0 ; back_emf = omega / kv_si
```

**Inputs.**

- [[motor-kv-si|Motor speed constant in SI]]

**Produced by.** `app/services/powertrain_performance.py:529` — `solve_qprop_operating_point.current_for_rpm`

**Consumed by.**

- in this graph: `Terminal current at a candidate RPM`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:530`

**Source.** 🟢 SOURCED

> Drela, M., 'DC Motor / Propeller Matching' theory notes, §1.1 and §1.1.3: v_m(Omega) = Omega / K_V — the internal back-EMF is proportional to rotation rate; terminal voltage v(i,Omega) = Omega/K_V + i R.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
v_m = Omega / K_V
```

**Cited in the code itself.** `docstring: "back-EMF / speed:   ω/Kv_si = V_terminal − I·Rm"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
