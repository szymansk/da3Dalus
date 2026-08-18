---
name: delta-sh-m2
symbol: ΔS_H
kind: quantity
unit: m²
cluster: stability
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
  - audit/confirmed
  - flag/divergence
---

# Required horizontal tail area change

**Definition.** Change in horizontal tail area needed to reach the target static margin.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
delta_sh_m2 = delta_needed / dsm_dsh  # m² (negative = shrink HS)
```

**Inputs.**

- [[sm-delta-needed|SM shortfall to target]]
- [[dsm-dsh|SM sensitivity to horizontal tail area]]

**Produced by.** `app/services/sm_sizing_service.py:413` — `suggest_corrections`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Horizontal tail chord-scale fraction`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/sm_sizing_service.py:414,443`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §6.7.1 — the tail area is solved from the volume-coefficient definition S_h = V_H·C̄·S/l, and tail area is the primary lever for adjusting longitudinal stability (§11.6.2, "Increasing tail area moves the neutral point aft").
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
S_h = V_H · C̄ · S / l  (Sadraey §6.7.1, from Eq. 11.20)
```

**⚠️ Divergence from the source.** Sadraey re-solves S_h from a target V_H; the code inverts a linearised sensitivity (ΔS_H = ΔSM/(dSM/dS_H)). Equivalent only for small changes.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
