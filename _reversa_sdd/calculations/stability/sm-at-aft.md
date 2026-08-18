---
name: sm-at-aft
symbol: SM_aft
kind: quantity
unit: – (fraction of MAC)
cluster: stability
user_visible: true
source_status: SOURCED
---

# Static margin at aft CG

**Definition.** Static margin evaluated at the most-aft loading CG; the quantity the aft-CG sizing loop drives to target.

**Formula — as the code writes it.**

```
sm_at_aft = (x_np_m - cg_aft_m) / mac_m
```

**Inputs.** [[mac-m-fallback|MAC fallback]]

**Produced by.** `app/services/sm_sizing_service.py:361` — `suggest_corrections`

**Consumed by.**

- in this graph: [[delta-sm-apply|Predicted SM change per apply]] · [[predicted-sm-htail-scale|Predicted SM after htail chord-scale]] · [[predicted-sm-wing-shift|Predicted SM after wing shift]] · [[sm-delta-needed|SM shortfall to target]]
- outside it: `app/services/sm_sizing_service.py:373,374,386,398,402,411,446,447` · `app/services/sm_sizing_service.py:770 (_load_apply_state, duplicate derivation)`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §11.6.2 Eq. 11.18 evaluated at the most-aft cg; the aft cg as the critical stability case is Sadraey §11.6.2 ("Both must hold across the operational envelope — including the most-aft cg") and §11.3.2.
>
> — via `aircraft-design-scholz + aerodynamics-expert`

**The source states it as.**

```
SM = (x_np − x_cg)/C̄, evaluated at x_cg,aft
```

**⚠️ Divergence from the source.** Formula matches. The code's own citation "Anderson §7.6 Eq. 7.41" (sm_sizing_service.py:361) is wrong — Anderson's "Fundamentals of Aerodynamics" 6e §7.6 is shock waves in compressible flow; the aerodynamic centre is §4.9. The static-margin material is in Anderson's "Introduction to Flight", not "Fundamentals of Aerodynamics".

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Derived here AND identically at line 770 in _load_apply_state — two copies of the same derivation. Also produced upstream as ctx['sm_at_aft'] by loading_scenario_service.enrich_context_with_cg_envelope:260 (rounded to 4 dp), so a third rounding-divergent copy exists.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `SM = (x_NP - x_CG) / MAC  (Anderson §7.6 Eq. 7.41, spec-gate A1)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
