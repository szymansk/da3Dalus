---
name: cg-loading-aft
symbol: x_cg,load,aft
kind: quantity
unit: m
cluster: mass
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/mass
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Aft loading CG

**Definition.** Aft-most CG produced by any user-defined loading scenario.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
"cg_loading_aft_m": max(cg_values)
```

**Inputs.**

- [[scenario-cg-x|Loading-scenario CG_x]]
- [[base-cg-x-default|Fallback base CG_x for scenario CG]]  — *ε tolerance*

**Produced by.** `app/services/loading_scenario_service.py:446` — `compute_loading_envelope_for_aeroplane`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `CG envelope violation distance` · `Static margin at aft loading CG (API)` · `Static margin at aft loading CG (cached)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/assumption_compute_service.py:796` · `app/services/loading_scenario_service.py:266 (ctx['cg_aft_m'])` · `app/services/loading_scenario_service.py:576/624 (CgEnvelopeRead)` · `app/services/sm_sizing_service.py:353 / :767 (reads ctx['cg_aft_m'])` · `app/services/tail_sizing_service.py:180 / :213 (l_h_eff_from_aft_cg_m)` · `frontend/hooks/useLoadingScenarios.ts:87`

**Source.** 🟢 SOURCED

> Sadraey, M.H., Wiley 2013, §11.5, Eq. (11.14) and steps 4–5: the most-aft cg X_cg_aft is obtained by removing every removable load whose cg lies FORWARD of X_cg1 and iterating until no removable element remains forward of the candidate. Non-dimensional range: Eq. (11.16), Δx_cg = (x_cg_aft − x_cg_for)/C̄.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
x_cg2 = ( Σ_{j=1..n} x_cg_j·m_j − Σ_{j=1..k1}(x_cg_j·m_j)_removed ) / ( Σ_{j=1..n} m_j − Σ_{j=1..k1} m_j_removed )   (Sadraey Eq. 11.14), iterated to convergence ⇒ X_cg_aft
```

**⚠️ Divergence from the source.** Same as cg-loading-fwd: max() over enumerated scenarios is an inner bound on Sadraey's deterministic extremum. This matters more on the aft side, because the aft CG is the stability-critical one (Sadraey §11.6.2 Eq. 11.22) and it is what tail_sizing_service.py:180/:213 and sm_sizing_service.py:353/:767 consume — an under-estimated aft CG propagates into a tail that is sized too small.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `"cg_loading_aft = max(cg_x over all scenarios)" — app/services/loading_scenario_service.py:7`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
