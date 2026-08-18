---
name: neutral-point-x-solver
symbol: X_np
kind: quantity
unit: m
cluster: stability
user_visible: true
source_status: SOURCED
node_class: solver-output
tags:
  - cluster/stability
  - class/solver-output
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
  - solver/aerobuildup
---

# Neutral point (solver)

**Definition.** Longitudinal neutral point taken directly from the aerodynamic solver's reference block.

**Solver output — a boundary of this graph.** The value is produced by an external solver, not by this application. There is no formula to source and no arithmetic to test here: the solver is trusted.

**What must be tested is what was handed in.** Every defect this application can commit at this boundary is an input defect — a wrong reference area, the wrong wing, an operating point that does not match the geometry, a unit that was not converted. See [[_solver-boundaries]] for the input set of each solver.
*Solver: **aerobuildup**.*

**Formula — as the code writes it.**

```
xnp = _scalar(result.reference.Xnp)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/stability_service.py:322` — `get_stability_summary`

**Consumed by.**

- in this graph: `Aft CG limit from margin bounds` · `Forward CG limit from margin bounds` · `Static margin (fraction of MAC)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/stability_service.py:328,334,338` · `app/services/copilot_tools.py:444`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §11.4 (neutral point definition; typically 40–50 % MAC for a fixed configuration) and §11.6.2 Eq. 11.17/11.22. Formal definition also in exam-tail-volume-coefficient concept: x_NP = x_ac,wing + V_H·(S_W/c̄)·(dc_m/dC_L)_tail.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
X_np: the point about which dC_m/dα = 0 for the complete aircraft
```

**⚠️ Divergence from the source.** The code does not compute the neutral point; it reads it from the solver reference block (result.reference.Xnp, app/services/stability_service.py:322). That is a valid tool output, not a literature formula — the sourcing above attributes the quantity, not the extraction.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Second producer of the same quantity: assumption_compute_service._stability_run_at_cruise:1079 also extracts result.reference.Xnp at a different operating point and stores it as ctx['x_np_m'] — copilot_tools.py:438-444 explicitly prefers the ctx one because the two diverge (gh-924).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
