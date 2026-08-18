---
name: vlm-drag-direction
symbol: d_hat
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: false
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
---

# Unit freestream (drag) direction

**Definition.** Normalised steady freestream direction used to project the strip force into drag.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
d_hat = np.asarray(vlm.steady_freestream_direction, dtype=float); d_hat = d_hat / np.linalg.norm(d_hat)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/vlm_strip_forces.py:227` — `compute_vlm_strip_forces`

**Consumed by.**

- in this graph: `Unit lift direction` · `Strip drag force`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §1.5 (drag = component of resultant force parallel to V_inf)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
D = R . (V_inf / |V_inf|)
```

**Cited in the code itself.** `app/services/vlm_strip_forces.py:227-228`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
