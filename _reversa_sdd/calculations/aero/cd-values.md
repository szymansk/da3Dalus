---
name: cd-values
symbol: C_D
kind: quantity
unit: -
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
---

# Drag coefficient array

**Definition.** CD vs alpha from the AeroBuildup solver result (total drag, not parasite only).

**Formula — as the code writes it.**

```
np.atleast_1d(np.asarray(result.coefficients.CD, dtype=float))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:96` — `_extract_alpha_sweep_arrays`

**Consumed by.**

- in this graph: [[drag-at-zero-lift-point|Drag at zero lift point]] · [[ld-ratio-coefficient|Lift-to-drag ratio (coefficient form)]] · [[min-cd-point|Minimum drag coefficient point]] · [[speed-polar-ld|Glide ratio per point]] · [[speed-polar-w|Sink rate]] · [[stall-point|Stall point]] · [[trim-point-cm-zero|Trim point (Cm = 0)]]
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
