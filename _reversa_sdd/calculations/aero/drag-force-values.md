---
name: drag-force-values
symbol: D
kind: quantity
unit: N
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
node_class: solver-output
tags:
  - cluster/aero-spanwise
  - class/solver-output
  - source/sourced
  - surface/user-visible
  - solver/aerobuildup
---

# Drag force array

**Definition.** Dimensional drag D vs alpha from result.forces.

**Solver output — a boundary of this graph.** The value is produced by an external solver, not by this application. There is no formula to source and no arithmetic to test here: the solver is trusted.

**What must be tested is what was handed in.** Every defect this application can commit at this boundary is an input defect — a wrong reference area, the wrong wing, an operating point that does not match the geometry, a unit that was not converted. See [[_solver-boundaries]] for the input set of each solver.
*Solver: **aerobuildup**.*

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
