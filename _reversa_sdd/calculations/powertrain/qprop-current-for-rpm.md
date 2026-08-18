---
name: qprop-current-for-rpm
symbol: I(n)
kind: quantity
unit: A
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
---

# Terminal current at a candidate RPM

**Definition.** Motor terminal current implied by the back-EMF relation at a candidate RPM: the voltage left over after back-EMF, divided by winding resistance.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return (V_terminal - back_emf) / rm
```

**Inputs.**

- [[qprop-back-emf|Motor back-EMF]]
- [[curve-v-terminal|Motor terminal voltage]]
- [[motor-rm-ohm-input|Winding resistance]]

**Produced by.** `app/services/powertrain_performance.py:530` — `solve_qprop_operating_point.current_for_rpm`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Solved terminal current` · `Motor-produced torque`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:534` · `app/services/powertrain_performance.py:578`

**Source.** 🟢 SOURCED

> Drela, 'DC Motor / Propeller Matching', §1.1: V = i*R + Omega/K_v, solved for current.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
V = i R + Omega/K_v  =>  i = (V - Omega/K_v) / R
```

**Cited in the code itself.** `docstring: "Terminal current implied by the back-EMF relation at this RPM."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
