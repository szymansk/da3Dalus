---
name: sm-at-aft-ctx
symbol: SM_aft
kind: quantity
unit: fraction of MAC
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
  - flag/anomaly
  - flag/divergence
---

# Static margin at aft loading CG (cached)

**Definition.** Static margin when the aircraft is loaded to its aft-most scenario CG, cached in assumption_computation_context. This is the stability-critical case.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
sm_at_aft = round((x_np - cg_loading_aft_m) / mac, 4)
```

**Inputs.**

- [[x-np|Neutral point]]  — *⊣ limit*
- [[cg-loading-aft|Aft loading CG]]
- [[mac|Mean aerodynamic chord (main wing)]]

**Produced by.** `app/services/loading_scenario_service.py:260` — `enrich_context_with_cg_envelope`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/loading_scenario_service.py:268 (ctx['sm_at_aft'])` · `app/services/sm_sizing_service.py:348 (ctx.get('sm_at_aft'))` · `app/services/sm_sizing_service.py:768`

**Source.** 🟢 SOURCED

> Sadraey, M.H., Wiley 2013, §11.6.2 Eq. (11.18), SM = (x_np − x_cg)/C̄, evaluated at the most-aft cg X_cg_aft from §11.5 Eq. (11.14). Sadraey §11.6.2 Eq. (11.22) makes this the binding stability constraint: x_np − x_cg > 0 "must hold across the operational envelope — including the most-aft cg from the forward-aft-cg technique."
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
SM = (x_np − x_cg) / C̄   (Eq. 11.18);  binding condition x_np − x_cg > 0   (Eq. 11.22)
```

**⚠️ Divergence from the source.** The source treats this as the single stability-critical static margin; the code computes it three times over (cached at loading_scenario_service.py:260 rounded to 4 dp, recomputed unrounded at :594 with a different target_sm default, re-derived a third time at sm_sizing_service.py:361). Sadraey's method has exactly one aft cg and one SM at it.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Two independent producers: this cached value and get_cg_envelope's on-the-fly recomputation at line 594 (unrounded, and using a different target_sm default). sm_sizing_service also re-derives it a third time at line 361 when the cached key is absent.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
