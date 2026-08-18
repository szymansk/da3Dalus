---
name: xnp-values
symbol: X_np
kind: quantity
unit: m
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
  - flag/anomaly
  - flag/divergence
  - solver/aerobuildup
---

# Longitudinal neutral point array

**Definition.** Xnp vs alpha pulled from result.reference.

**Solver output — a boundary of this graph.** The value is produced by an external solver, not by this application. There is no formula to source and no arithmetic to test here: the solver is trusted.

**What must be tested is what was handed in.** Every defect this application can commit at this boundary is an input defect — a wrong reference area, the wrong wing, an operating point that does not match the geometry, a unit that was not converted. See [[_solver-boundaries]] for the input set of each solver.
*Solver: **aerobuildup**.*

**Formula — as the code writes it.**

```
np.atleast_1d(np.asarray(result.reference.Xnp, dtype=float))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:862` — `_extract_reference_arrays`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Neutral-point sensitivity metric` · `Series span` · `Xnp outlier deviation`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_plot_neutral_points` · `_classify_variation` · `_render_summary_panel`

**Source.** 🟢 SOURCED

> Sadraey, Aircraft Design: A Systems Engineering Approach (Wiley 2013), §11.6.2 Eq. 11.17/11.18; Anderson 6e §4.x (aerodynamic centre, dc_m/dα = 0)
>
> — via `aircraft-design-scholz, aerodynamics-expert`

**The source states it as.**

```
C_mα = C_Lα * (X_cg − X_np)  (11.17);  SM = (x_np − x_cg)/C̄  (11.18)
```

**⚠️ Divergence from the source.** Sadraey's X_np is NON-DIMENSIONAL (fraction of MAC); the code carries Xnp in metres. Any threshold applied to it therefore is not comparable to literature static-margin bands.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Only reaches the user through the alpha-sweep PNG; the JSON alpha_sweep response does not carry Xnp.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
