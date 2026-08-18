---
name: clb
symbol: Cl_beta
kind: quantity
unit: 1/rad
cluster: stability
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
  - surface/user-visible
---

# Rolling moment derivative w.r.t. beta

**Definition.** dCl/dbeta at the analysed operating point. Negative means laterally stable (dihedral effect).

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
clb = _scalar(result.derivatives.Clb)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/stability_service.py:326` — `get_stability_summary`

**Consumed by.**

- in this graph: `Lateral stability flag`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/stability_service.py:344,347` · `app/services/stability_service.py:172` · `app/services/copilot_tools.py:458`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §6.2.2 ("lateral stability (C_lβ < 0)"), restated in §12.3.3 (lateral-directional handling qualities) and §12.6.2 ("C_lβ < 0 (dihedral effect, stabilizing)").
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
C_lβ < 0 — dihedral effect, stabilizing
```

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
