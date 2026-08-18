---
name: x-np
symbol: x_NP
kind: quantity
unit: m
cluster: mass
user_visible: true
source_status: SOURCED
node_class: solver-output
tags:
  - cluster/mass
  - class/solver-output
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
  - solver/aerobuildup
---

# Neutral point

**Definition.** Longitudinal position of the aircraft's neutral point from the AeroBuildup stability run at cruise; the datum for every CG limit and static margin in this cluster.

**Solver output — a boundary of this graph.** The value is produced by an external solver, not by this application. There is no formula to source and no arithmetic to test here: the solver is trusted.

**What must be tested is what was handed in.** Every defect this application can commit at this boundary is an input defect — a wrong reference area, the wrong wing, an operating point that does not match the geometry, a unit that was not converted. See [[_solver-boundaries]] for the input set of each solver.
*Solver: **aerobuildup**.*

**Formula — as the code writes it.**

```
x_np = _scalar(result.reference.Xnp)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/assumption_compute_service.py:1079` — `_stability_run_at_cruise`

**Consumed by.**

- in this graph: `Aft CG stability limit` · `Forward CG stability limit (0.30·MAC stub)` · `Design CG_x (aerodynamic CG target)` · `Static margin at aft loading CG (API)` · `Static margin at aft loading CG (cached)` · `Static margin at forward loading CG (API)` · `Static margin at forward loading CG (cached)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/assumption_compute_service.py:108 (cg_x)` · `app/services/assumption_compute_service.py:473 (compute_stability_envelope)` · `app/services/assumption_compute_service.py:725 (ctx['x_np_m'])` · `app/services/loading_scenario_service.py:112 / :116 / :259 / :260 / :593 / :594` · `app/services/sm_sizing_service.py:354 / :509 / :769` · `app/services/tail_sizing_service.py:179` · `app/services/elevator_authority_service.py:237 / :362 / :497` · `frontend/lib/metricsAdapters.ts:344`

**Source.** 🟢 SOURCED

> Sadraey, M.H., Wiley 2013, §11.6.2 Eq. (11.17): C_mα = C_Lα·(X_cg − X_np), which defines X_np as the cg at which C_mα = 0 ("the aircraft aerodynamic center"); §11.4: "The neutral point is approximately fixed for a fixed configuration and typically lies at 40–50% MAC." RC treatment: Lennon, A., "Basics of R/C Model Aircraft Design", Air Age 1996, Ch. 6 'CG Location' — wing and tailplane treated as tandem airfoils whose combined lift acts at the NP, which "lies between the two aerodynamic centers and closer to the larger lift producer"; Lennon places the power-on NP at 35% MAC for models, moving a few points aft power-off.
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
C_mα = C_Lα · ( X_cg − X_np )   (Sadraey Eq. 11.17); stability requires C_mα < 0 ⇔ X_cg < X_np (Eq. 11.22)
```

**⚠️ Divergence from the source.** Two formal differences from the sources, neither a defect by itself. (1) Sadraey's X_np is NON-DIMENSIONAL — a fraction of MAC measured from the wing leading edge at MAC (his Eq. 11.11 convention); the code's x_np is a dimensional metre coordinate in the AeroSandbox body frame. SM = (x_np − x_cg)/MAC is only correct if x_cg uses the identical datum, which the code never asserts. (2) The code obtains X_np from an AeroBuildup stability run rather than from Eq. (11.17); that is a legitimate substitution (a solver evaluating the same definition) but it means the sourced sanity band — 40–50% MAC per Sadraey §11.4, 35% MAC for models per Lennon Ch. 6 — is never checked against the solver's answer. The dual access path noted in the inventory (ctx['x_np_m'] versus the 'x_np' design-assumption key read by elevator_authority_service.py:497) has no counterpart in any source: Sadraey has one neutral point.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** elevator_authority_service reads x_np from the design-assumption store under the key 'x_np' (line 497), while every other consumer reads ctx['x_np_m'] — two access paths that can go out of sync on a cold start (handled defensively at assumption_compute_service.py:501-516).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"Uses analyse_aerodynamics → AnalysisModel for x_np (same path as stability_service, keeps NP consistent across the app)." — app/services/assumption_compute_service.py:1072-1073`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
