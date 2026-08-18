---
name: cdftp-cd-clean
symbol: cd_clean
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

# Clean section drag (installed-turbulator path)

**Definition.** Section cd at natural transition for the installed-position ΔCD0 calculation.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cd_clean = _cd_at_cl_xtr(airfoil, sec.cl, sec.re_local, xtr_upper=1.0)
```

**Inputs.**

- [[tos-cd-at-cl|Section cd at a target CL and trip position]]

**Produced by.** `app/services/turbulator_optimizer_service.py:693` — `compute_delta_cd0_from_turbulator_position`

**Consumed by.**

- in this graph: `Section drag delta (installed turbulator)` · `Per-section failure warnings`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> Sharpe, PhD thesis (MIT, 2024) §7.2.5 (natural transition is the untripped baseline case)
>
> — via `aerosandbox-expert`

**The source states it as.**

```
cd_clean = cd(cl, Re; xtr_upper = 1.0)
```

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:693`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
