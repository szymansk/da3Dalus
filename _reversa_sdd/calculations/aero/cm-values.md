---
name: cm-values
symbol: C_m
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

# Pitching-moment coefficient array

**Definition.** Cm vs alpha from the solver result, used for trim and longitudinal-stability classification.

**Solver output — a boundary of this graph.** The value is produced by an external solver, not by this application. There is no formula to source and no arithmetic to test here: the solver is trusted.

**What must be tested is what was handed in.** Every defect this application can commit at this boundary is an input defect — a wrong reference area, the wrong wing, an operating point that does not match the geometry, a unit that was not converted. See [[_solver-boundaries]] for the input set of each solver.
*Solver: **aerobuildup**.*

**Formula — as the code writes it.**

```
np.atleast_1d(np.asarray(result.coefficients.Cm, dtype=float))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:98` — `_extract_alpha_sweep_arrays`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Local Cm gradient` · `Longitudinal stability slope` · `Trim nearest-point fallback` · `Trim point (Cm = 0)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_compute_trim_point` · `_classify_longitudinal_stability` · `_plot_cm_stability` · `frontend useAnalysis`

**Source.** 🟢 SOURCED

> Anderson 6e §1.5 (moment coefficient); AeroSandbox docs_aero_3d.md 'Return Value Conventions'
>
> — via `aerodynamics-expert, aerosandbox-expert`

**The source states it as.**

```
C_M = M / (q_inf * S * l)  [Anderson §1.5]; ASB: Cm = m_b/(q*S_ref*c_ref), body axes, about xyz_ref
```

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
