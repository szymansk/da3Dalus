---
name: drag-force-values
symbol: D
kind: quantity
unit: N
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/sourced
  - surface/user-visible
---

# Drag force array

**Definition.** Dimensional drag D vs alpha from result.forces.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
np.atleast_1d(np.asarray(result.forces.D, dtype=float))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:881` — `_extract_force_arrays`

**Consumed by.**

- in this graph: `Glide ratio from forces`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_plot_glide_ratio`

**Source.** 🟢 SOURCED

> Anderson 6e §1.5; AeroSandbox docs_aero_3d.md 'Return Value Conventions'
>
> — via `aerodynamics-expert, aerosandbox-expert`

**The source states it as.**

```
D = wind-axis force along V; ASB D = -F_w[0] [N]
```

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
