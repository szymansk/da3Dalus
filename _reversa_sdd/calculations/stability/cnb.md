---
name: cnb
symbol: Cn_beta
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

# Yawing moment derivative w.r.t. beta

**Definition.** dCn/dbeta at the analysed operating point. Positive means directionally stable.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cnb = _scalar(result.derivatives.Cnb)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/stability_service.py:325` — `get_stability_summary`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Directional stability flag`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/stability_service.py:343,346` · `app/services/stability_service.py:171` · `app/services/copilot_tools.py:457`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §6.2.2 (directional stability requirement C_nβ > 0) and §6.7 Eq. 6.73: C_nβ ≈ K_f1·C_Lα,v·(1 − dσ/dβ)·η_v·(l_vt·S_v)/(b·S).
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
C_nβ ≈ K_f1 · C_Lα,v · (1 − dσ/dβ) · η_v · l_vt·S_v/(b·S) ;  stable ⇔ C_nβ > 0
```

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
