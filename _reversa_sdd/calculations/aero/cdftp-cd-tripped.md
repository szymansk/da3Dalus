---
name: cdftp-cd-tripped
symbol: cd_tripped
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: false
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
---

# Tripped section drag (installed-turbulator path)

**Definition.** Section cd at the installed trip position.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cd_tripped = _cd_at_cl_xtr(airfoil, sec.cl, sec.re_local, xtr_upper=xtr_sec)
```

**Inputs.**

- [[tos-cd-at-cl|Section cd at a target CL and trip position]]
- [[cdftp-xtr-sec|Section trip position from the installed turbulator]]

**Produced by.** `app/services/turbulator_optimizer_service.py:694` — `compute_delta_cd0_from_turbulator_position`

**Consumed by.**

- in this graph: `Section drag delta (installed turbulator)` · `Per-section failure warnings`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> Sharpe, PhD thesis (MIT, 2024) §7.2.5 (forced trip location x_tr,forced/c as a trained model input)
>
> — via `aerosandbox-expert`

**The source states it as.**

```
cd_tripped = cd(cl, Re; xtr_upper = xtr_installed)
```

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:694`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
