---
name: sm-fwd
symbol: SM_fwd
kind: quantity
unit: – (fraction of MAC)
cluster: stability
user_visible: true
source_status: SOURCED
---

# Static margin at forward CG

**Definition.** Static margin evaluated at the most-forward loading CG.

**Formula — as the code writes it.**

```
sm_fwd: float = (x_np_m - cg_fwd_actual) / mac_m
```

**Inputs.** [[mac-m-fallback|MAC fallback]]

**Produced by.** `app/services/sm_sizing_service.py:508` — `_suggest_corrections_fwd`

**Consumed by.**

- in this graph: [[predicted-sm-fwd-htail|Predicted forward SM after htail scale]] · [[sm-deficit-fwd|Forward-CG SM excess]]
- outside it: `app/services/sm_sizing_service.py:516,521,527,529,538,552,556,575,576,580`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §11.6.2 Eq. 11.18 evaluated at the most-forward cg; forward-cg evaluation mandated by §11.6.3 and §12.5.5 step 17.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
SM_fwd = (x_np − x_cg,fwd)/C̄
```

**⚠️ Anomaly.** Also produced upstream, rounded, as ctx['sm_at_fwd'] by loading_scenario_service.enrich_context_with_cg_envelope:259 — two producers of the same number.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `SM_fwd = (x_NP - cg_fwd_actual) / MAC`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
