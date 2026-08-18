---
name: cg-x-from-xyz-ref
symbol: X_cg
kind: quantity
unit: m
cluster: stability
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/divergence
---

# CG x used for static margin

**Definition.** Longitudinal CG used as the moment reference; taken as the first component of the operating point's xyz_ref.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
xcg = float(operating_point.xyz_ref[0]) if operating_point.xyz_ref else None
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/stability_service.py:323` — `get_stability_summary`

**Consumed by.**

- in this graph: `Static margin (fraction of MAC)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/stability_service.py:328,339` · `app/services/stability_service.py:165 (cg_x_used column)` · `app/services/copilot_tools.py:446,455`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §11.6.2 — the pitching-moment derivative C_mα is defined about the aircraft cg (Eq. 11.17); the moment reference point for stability derivatives must therefore be the cg. Same convention in AeroSandbox (asb solvers take xyz_ref as the moment reference) — AeroSandbox docs, aero_3d / AeroBuildup class reference.
>
> — via `aircraft-design-scholz + aerosandbox-expert`

**⚠️ Divergence from the source.** Sadraey's x_cg is a physically determined mass property; the code takes whatever the operating point carries in xyz_ref[0]. The app's own converter defaults xyz_ref to [0,0,0] (app/schemas/aeroplaneschema.py:93-94), so an unset operating point silently makes the moment reference the nose datum, not the cg — and the static margin is then not a static margin.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
