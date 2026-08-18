---
name: static-margin-fraction
symbol: SM
kind: quantity
unit: – (fraction of MAC)
cluster: stability
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Static margin (fraction of MAC)

**Definition.** Longitudinal static stability margin: distance from CG to neutral point, normalised by the mean aerodynamic chord.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return (xnp - xcg) / mac
```

**Inputs.**

- [[neutral-point-x-solver|Neutral point (solver)]]
- [[cg-x-from-xyz-ref|CG x used for static margin]]
- [[mac-solver-cref|MAC (solver reference chord)]]

**Produced by.** `app/services/stability_service.py:52` — `_compute_static_margin`

**Consumed by.**

- in this graph: `Static margin percent`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/stability_service.py:329 (→ static_margin_pct)` · `app/services/stability_service.py:337 (StabilitySummaryResponse.static_margin)` · `app/api/v2/endpoints/aeroanalysis.py:203` · `app/mcp_server.py:1184 compute_stability tool`

**Source.** 🟢 SOURCED

> Sadraey, "Aircraft Design: A Systems Engineering Approach" (Wiley 2013), §11.6.2, Eq. 11.18. Corroborated: Scholz HAW Hamburg, 10_BoxWingSystematic §4.2 ("Stability margin = (NP − CG) / Mean aerodynamic chord").
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
SM = (x_np − x_cg) / C̄   (Sadraey Eq. 11.18)
```

**⚠️ Divergence from the source.** Form is identical. Reference frames are not: Sadraey non-dimensionalises about the MAC leading edge (Eq. 11.11, h = (x_cg − x_LE_MAC)/C̄), whereas the code takes x_cg from operating_point.xyz_ref[0] (app/services/stability_service.py:323) and the chord from the solver's reference block (result.reference.Cref, :327). The result is the same number only if the solver's Cref really is the wing MAC and xyz_ref really is the CG — neither is checked.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Three independent producers of static margin exist (see notes F2): this one, copilot_tools.py:446-447, and trim_enrichment_service.py:146 (-Cm_a/CL_a). No frontend component reads this value.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"""Compute static margin: (Xnp - Xcg) / MAC."""`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
