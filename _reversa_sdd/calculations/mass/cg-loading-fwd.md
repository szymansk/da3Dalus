---
name: cg-loading-fwd
symbol: x_cg,load,fwd
kind: quantity
unit: m
cluster: mass
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/mass
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/divergence
---

# Forward loading CG

**Definition.** Forward-most CG produced by any user-defined loading scenario.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
"cg_loading_fwd_m": min(cg_values)
```

**Inputs.**

- [[scenario-cg-x|Loading-scenario CG_x]]
- [[base-cg-x-default|Fallback base CG_x for scenario CG]]  — *ε tolerance*

**Produced by.** `app/services/loading_scenario_service.py:445` — `compute_loading_envelope_for_aeroplane`

**Consumed by.**

- in this graph: `CG envelope violation distance` · `Static margin at forward loading CG (API)` · `Static margin at forward loading CG (cached)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/assumption_compute_service.py:795` · `app/services/loading_scenario_service.py:265 (ctx['cg_forward_m'])` · `app/services/loading_scenario_service.py:575/623 (CgEnvelopeRead)` · `app/services/sm_sizing_service.py:499 (reads ctx['cg_forward_m'])` · `frontend/hooks/useLoadingScenarios.ts:86`

**Source.** 🟢 SOURCED

> Sadraey, M.H., Wiley 2013, §11.5 ("Technique to Determine Forward and Aft Center of Gravity"), Eq. (11.15) and steps 6–7: the most-forward cg X_cg_for is obtained by removing every removable load whose cg lies AFT of X_cg1 and iterating until no removable element remains aft of the candidate.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
x_cg3 = ( Σ_{j=1..n} x_cg_j·m_j − Σ_{j=1..k2}(x_cg_j·m_j)_removed ) / ( Σ_{j=1..n} m_j − Σ_{j=1..k2} m_j_removed )   (Sadraey Eq. 11.15), iterated to convergence ⇒ X_cg_for
```

**⚠️ Divergence from the source.** The code takes min() over an enumerated list of user-authored scenarios. Sadraey §11.5 replaces exactly that with a deterministic 8-step search and states why: "The procedure is monotone and terminates in a finite number of steps… no scenario can be missed because removable loads are tested directly against the candidate extremum." min(user scenarios) is a lower bound on the true forward extremum, not the extremum — if the user never authors the loading that produces it, the app reports a forward CG that is not the forward CG. The code has all the ingredients (per-component masses, positions, toggles) to run Sadraey's iteration instead.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `"Loading-Envelope:  what user-defined loading scenarios produce. cg_loading_fwd = min(cg_x over all scenarios)" — app/services/loading_scenario_service.py:5-6`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
