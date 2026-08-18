---
name: lift-force-values
symbol: L
kind: quantity
unit: N
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
---

# Lift force array

**Definition.** Dimensional lift L vs alpha from result.forces.

**Formula — as the code writes it.**

```
np.atleast_1d(np.asarray(result.forces.L, dtype=float))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:879` — `_extract_force_arrays`

**Consumed by.**

- in this graph: [[ld-ratio-force|Glide ratio from forces]]
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
