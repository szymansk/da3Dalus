---
name: xnp-lat-values
symbol: X_np,lat
kind: quantity
unit: m
cluster: aero-spanwise
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: solver-output
tags:
  - cluster/aero-spanwise
  - class/solver-output
  - source/no-source-found
  - surface/user-visible
  - solver/aerobuildup
---

# Lateral neutral point array

**Definition.** Xnp_lat vs alpha pulled from result.reference.

**Solver output — a boundary of this graph.** The value is produced by an external solver, not by this application. There is no formula to source and no arithmetic to test here: the solver is trusted.

**What must be tested is what was handed in.** Every defect this application can commit at this boundary is an input defect — a wrong reference area, the wrong wing, an operating point that does not match the geometry, a unit that was not converted. See [[_solver-boundaries]] for the input set of each solver.
*Solver: **aerobuildup**.*

**Formula — as the code writes it.**

```
np.atleast_1d(np.asarray(result.reference.Xnp_lat, dtype=float))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:868` — `_extract_reference_arrays`

**Consumed by.**

- in this graph: `Neutral-point sensitivity metric` · `Series span` · `Xnp_lat jump` · `Xnp_lat outlier deviation`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_collect_xnp_lat_labels` · `_compute_neutral_strip_colors` · `_classify_variation`

**Source.** 🔴 NO SOURCE FOUND

> No definition of a 'lateral neutral point' station found in Sadraey §11.6, Scholz, or Anderson 6e — directional stability is treated via C_nβ, not an x-station analogue. Xnp_lat is a solver-specific output.
>
> — via `aircraft-design-scholz, aerodynamics-expert`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
