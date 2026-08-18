---
name: cl-values
symbol: C_L
kind: quantity
unit: -
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: solver-output
tags:
  - cluster/aero-spanwise
  - class/solver-output
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - solver/aerobuildup
---

# Lift coefficient array

**Definition.** CL vs alpha from the AeroBuildup solver result.

**Solver output — a boundary of this graph.** The value is produced by an external solver, not by this application. There is no formula to source and no arithmetic to test here: the solver is trusted.

**What must be tested is what was handed in.** Every defect this application can commit at this boundary is an input defect — a wrong reference area, the wrong wing, an operating point that does not match the geometry, a unit that was not converted. See [[_solver-boundaries]] for the input set of each solver.
*Solver: **aerobuildup**.*

**Formula — as the code writes it.**

```
np.atleast_1d(np.asarray(result.coefficients.CL, dtype=float))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:94` — `_extract_alpha_sweep_arrays`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Alpha at best glide` · `Alpha at minimum sink` · `CL max for stall speed` · `Drag at zero lift point` · `Lift-to-drag ratio (coefficient form)` · `Maximum lift coefficient point` · `Glide ratio per point` · `Glide forward speed` · `Sink rate` · `Stall point` · `Trim point (Cm = 0)` · `Zero-lift nearest-point fallback`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_compute_cl_cd_points` · `_compute_trim_point` · `_build_speed_polar` · `_plot_coefficient_curves` · `copilot_tools:366` · `frontend useAnalysis`

**Source.** 🟢 SOURCED

> Anderson 6e §1.5 (force coefficients); AeroSandbox docs_aero_3d.md 'Return Value Conventions'
>
> — via `aerodynamics-expert, aerosandbox-expert`

**The source states it as.**

```
C_L = L / (q_inf * S), q_inf = 0.5*rho_inf*V_inf^2  [Anderson §1.5]; ASB: CL = L/(q*S_ref)
```

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
