---
name: cl-values
symbol: C_L
kind: quantity
unit: -
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
---

# Lift coefficient array

**Definition.** CL vs alpha from the AeroBuildup solver result.

**Formula — as the code writes it.**

```
np.atleast_1d(np.asarray(result.coefficients.CL, dtype=float))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:94` — `_extract_alpha_sweep_arrays`

**Consumed by.**

- in this graph: [[alpha-best-glide-deg|Alpha at best glide]] · [[alpha-min-sink-deg|Alpha at minimum sink]] · [[cl-max-speed-polar|CL max for stall speed]] · [[drag-at-zero-lift-point|Drag at zero lift point]] · [[ld-ratio-coefficient|Lift-to-drag ratio (coefficient form)]] · [[max-cl-point|Maximum lift coefficient point]] · [[speed-polar-ld|Glide ratio per point]] · [[speed-polar-v|Glide forward speed]] · [[speed-polar-w|Sink rate]] · [[stall-point|Stall point]] · [[trim-point-cm-zero|Trim point (Cm = 0)]] · [[zero-crossing-fallback-index|Zero-lift nearest-point fallback]]
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
