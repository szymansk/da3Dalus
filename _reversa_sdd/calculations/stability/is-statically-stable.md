---
name: is-statically-stable
symbol: —
kind: quantity
unit: – (bool)
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
---

# Static stability flag

**Definition.** True when Cm_alpha is present and negative.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
is_statically_stable=(cma is not None and cma < 0)
```

**Inputs.**

- [[cma|Pitching moment derivative w.r.t. alpha]]

**Produced by.** `app/services/stability_service.py:345` — `get_stability_summary`

**Consumed by.**

- outside it: `app/services/stability_service.py:175` · `app/services/copilot_tools.py:459`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §11.6.2, Eq. 11.17: static longitudinal stability ⇔ C_mα < 0.
>
> — via `aircraft-design-scholz`

**⚠️ Anomaly.** Second producer with the same name and a different rule: trim_enrichment_service.py:140 `is_static = cm_a < 0 if has_cm_a else True` — missing data yields True (stable) there, False here.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
