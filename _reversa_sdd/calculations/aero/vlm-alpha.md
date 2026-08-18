---
name: vlm-alpha
symbol: alpha
kind: quantity
unit: deg
cluster: aero-strips
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
  - surface/user-visible
  - solver-adjacent/vlm
---

# Echoed angle of attack

**Definition.** Operating-point alpha echoed into the strip-forces result.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
"alpha": float(op_point.alpha),
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/vlm_strip_forces.py:315` — `compute_vlm_strip_forces`

**Consumed by.**

- outside it: `app/services/analysis_service.py:_build_strip_forces_response` · `app/services/spanwise_loads.py:114`

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §1.5 (angle of attack: angle between chord/body reference line and V_inf)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
alpha = angle between the body reference axis and the freestream
```

**Cited in the code itself.** `app/services/vlm_strip_forces.py:315`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
