---
name: end_p_req_vmd
symbol: P_req(V_md)
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

# Power required at V_md

**Definition.** Battery power at the minimum-drag speed.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
_power_required(rho=RHO_SEA_LEVEL, v=float(v_md), cd0=cd0_at_vmd, e=e_at_vmd, ar=float(ar), mass=mass, s_ref=float(s_ref), eta_total=eta_total)
```

**Inputs.**

- [[end_p_req|Battery power required]]

**Produced by.** `app/services/endurance_service.py:378` — `compute_endurance`

**Consumed by.**

- in this graph: `Power margin` · `Flight time at V_md`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `EnduranceCard.tsx` · `metricsAdapters.toPowertrainItems`

**Source.** 🟢 SOURCED

> P_req evaluated at V_md; minimum-drag speed condition C_D0 = k*C_L^2, Anderson 6e §6.7.3 and Scholz 05_PreliminarySizing §5.7 Eq. 5.39.
>
> — via `scholz, aero`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
