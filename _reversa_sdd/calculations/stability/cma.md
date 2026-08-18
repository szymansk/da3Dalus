---
name: cma
symbol: Cm_alpha
kind: quantity
unit: 1/rad
cluster: stability
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
---

# Pitching moment derivative w.r.t. alpha

**Definition.** dCm/dalpha at the analysed operating point. Negative means longitudinally stable.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cma = _scalar(result.derivatives.Cma)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/stability_service.py:324` — `get_stability_summary`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Static stability flag`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/stability_service.py:342,345` · `app/services/stability_service.py:170 (Cma column)` · `app/services/copilot_tools.py:456`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §11.6.2, Eq. 11.17: C_mα = C_Lα·(X_cg − X_np); static longitudinal stability requires C_mα < 0.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
C_mα = C_Lα · (X_cg − X_np)
```

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
