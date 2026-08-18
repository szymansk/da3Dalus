---
name: cd-values
symbol: C_D
kind: quantity
unit: -
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/divergence
---

# Drag coefficient array

**Definition.** CD vs alpha from the AeroBuildup solver result (total drag, not parasite only).

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
np.atleast_1d(np.asarray(result.coefficients.CD, dtype=float))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:96` — `_extract_alpha_sweep_arrays`

**Consumed by.**

- in this graph: `Drag at zero lift point` · `Lift-to-drag ratio (coefficient form)` · `Minimum drag coefficient point` · `Glide ratio per point` · `Sink rate` · `Stall point` · `Trim point (Cm = 0)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_compute_cl_cd_points` · `_build_speed_polar` · `_plot_drag_polar` · `copilot_tools:366` · `frontend useAnalysis`

**Source.** 🟢 SOURCED

> Anderson 6e §1.5 (C_D = D/(q_inf S)); AeroSandbox docs_aero_3d.md 'Return Value Conventions' + 'AeroBuildup'
>
> — via `aerodynamics-expert, aerosandbox-expert`

**The source states it as.**

```
C_D = D / (q_inf * S); ASB CD = D/(q*S_ref), D = wind-axis total drag
```

**⚠️ Divergence from the source.** ASB AeroBuildup CD is TOTAL drag (profile + induced + wave when include_wave_drag=True), not parasite. The inventory's definition is correct; consumers that read it as CD0 are wrong.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
