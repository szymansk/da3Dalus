---
name: lift-force-values
symbol: L
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

# Lift force array

**Definition.** Dimensional lift L vs alpha from result.forces.

**Solver output — a boundary of this graph.** The value is produced by an external solver, not by this application. There is no formula to source and no arithmetic to test here: the solver is trusted.

**What must be tested is what was handed in.** Every defect this application can commit at this boundary is an input defect — a wrong reference area, the wrong wing, an operating point that does not match the geometry, a unit that was not converted. See [[_solver-boundaries]] for the input set of each solver.
*Solver: **aerobuildup**.*

**Formula — as the code writes it.**

```
np.atleast_1d(np.asarray(result.forces.L, dtype=float))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:879` — `_extract_force_arrays`

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
L = wind-axis force perpendicular to V; ASB L = -F_w[2] [N]
```

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
