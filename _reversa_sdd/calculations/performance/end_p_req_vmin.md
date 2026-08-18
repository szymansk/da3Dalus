---
name: end_p_req_vmin
symbol: P_req(V_mp)
kind: quantity
unit: W
cluster: perf-envelope
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/sourced
  - surface/user-visible
---

# Power required at V_min_sink

**Definition.** Battery power at the minimum-power speed.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
_power_required(rho=RHO_SEA_LEVEL, v=float(v_min_sink), cd0=cd0_at_vmin, e=e_at_vmin, ar=float(ar), mass=mass, s_ref=float(s_ref), eta_total=eta_total)
```

**Inputs.**

- [[end_p_req|Battery power required]]

**Produced by.** `app/services/endurance_service.py:388` — `compute_endurance`

**Consumed by.**

- in this graph: `Maximum endurance`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `EnduranceCard.tsx`

**Source.** 🟢 SOURCED

> P_req at minimum-power speed; condition C_L = sqrt(3*C_D0/k), C_D = 4*C_D0 — Sadraey §4.2.5.4 (Eq. 4.22, (L/D)_Emax = 0.866*(L/D)_max) and §4.3 (V_Pmin = 0.76*V_Dmin).
>
> — via `scholz`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
