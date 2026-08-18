---
name: resolved-sigma-allow-plan
symbol: σ_allow
kind: parameter
unit: MPa (N/mm²)
cluster: structure
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-parameter
tags:
  - cluster/structure
  - class/unclassified-parameter
  - source/partial
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Allowable bending stress (plan path)

**Definition.** Allowable bending stress for the plan endpoint, from the request override or the material component, rejecting non-positive values with a 422.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Formula — as the code writes it.**

```
return float(sigma_allow)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_plan_service.py:344` — `_resolve_sigma_allow`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Station required section modulus (plan path)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_plan_service.py:554` · `app/services/spar_plan_service.py:568` · `cad_designer/airplane/geometry/spar_solver.py:765`

**Source.** 🟡 PARTIAL

> Kirch, "Hauptholm", https://www.flugmodellbau-kirch.de/Hauptholm.htm — σ_allowable in W_req = M/σ_allowable, with tabulated wood and steel values (pine grade A: 400 kg/cm² compression / 700 kg/cm² tension; steel 52.1: 3600 kg/cm²)
>
> — via `direct verification of the kirch source`

**The source states it as.**

```
W_req = M / σ_allowable (procedure step 2).
```

**⚠️ Divergence from the source.** Same relation as `sigma-allow-mpa`, resolved by a second, independent code path. No source justifies having two resolvers for one user-facing quantity (an ADR 0022 question). Additionally, unlike the sizing path this value is never echoed in SparPlanResponse, so the plan output does not state what σ it was sized for — the source's procedure treats σ_allowable as an explicit, recorded design input.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Second producer of the same user-facing quantity as app/services/spar_sizing.py:294; unlike the sizing path this value is NOT echoed in the response, so the plan output does not say what σ it was sized for.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
