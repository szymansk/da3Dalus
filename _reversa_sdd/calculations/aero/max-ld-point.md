---
name: max-ld-point
kind: quantity
unit: mixed (deg, -, -)
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

# Maximum L/D point

**Definition.** Sweep point with the largest CL/CD, reported as best-glide.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
i = int(np.nanargmax(ld)); {"alpha_deg": alpha[i], "CL": cl[i], "CD": cd[i], "lift_to_drag_ratio": ld[i]}
```

**Inputs.**

- [[ld-ratio-coefficient|Lift-to-drag ratio (coefficient form)]]
- [[alpha-array|Alpha sweep array]]

**Produced by.** `app/services/analysis_service.py:111` — `_compute_cl_cd_points`

**Consumed by.**

- in this graph: `Characteristic points dict`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `alpha-sweep PNG polar panel` · `_render_summary_panel` · `copilot_tools 'best_glide'` · `API alpha_sweep response`

**Source.** 🟢 SOURCED

> Anderson 6e §6.7.2; Scholz, Flugzeugentwurf (HAW Hamburg) 05_PreliminarySizing §5.7 Eq. 5.39
>
> — via `aerodynamics-expert, aircraft-design-scholz`

**The source states it as.**

```
d(C_L/C_D)/dC_L = 0  ⇒  C_D,0 = C_L^2/(π e AR);  C_L,md = sqrt(π A e C_D,0);  E_max = 0.5*sqrt(π A e / C_D,0)  (5.39)
```

**⚠️ Divergence from the source.** Both sources give the ANALYTIC optimum of the parabolic polar. The code takes np.nanargmax over the discrete α grid, so (L/D)max is resolution-limited and lands on a grid node, never on C_L,md. With a coarse alpha_num the reported best-glide α can be off by a full grid step.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
