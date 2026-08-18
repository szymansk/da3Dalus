---
name: static-margin-pct
symbol: SM %
kind: quantity
unit: % MAC
cluster: stability
user_visible: true
source_status: SOURCED
---

# Static margin percent

**Definition.** Static margin expressed in percent of MAC; the value persisted and classified.

**Formula — as the code writes it.**

```
static_margin_pct = static_margin * 100 if static_margin is not None else None
```

**Inputs.** [[static-margin-fraction|Static margin (fraction of MAC)]]

**Produced by.** `app/services/stability_service.py:329` — `get_stability_summary`

**Consumed by.**

- in this graph: [[stability-class|Stability classification (static margin band)]]
- outside it: `app/services/stability_service.py:350 classify_stability` · `app/services/stability_service.py:166 persist (static_margin_pct column)` · `app/services/copilot_tools.py:445,452` · `frontend/components/workbench/MarkerDetailBox.tsx:16 (component never mounted)`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §11.4, Eq. 11.11–11.13 (longitudinal CG expressed as percentage of MAC); §11.6.2 Eq. 11.18 for the underlying SM.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
h = (x_cg − x_LE_MAC)/C̄, conventionally reported in % MAC
```

**⚠️ Anomaly.** copilot_tools.py:446-447 recomputes this number with a different formula and overrides it — two producers of one user-visible quantity (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
