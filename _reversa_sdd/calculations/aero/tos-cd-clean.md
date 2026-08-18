---
name: tos-cd-clean
symbol: cd_clean
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
---

# Natural-transition section drag

**Definition.** Section cd with no turbulator, evaluated at xtr_upper = 1.0.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cd_clean = _cd_at_cl_xtr(airfoil, cl, re, xtr_upper=1.0)
```

**Inputs.**

- [[tos-cd-at-cl|Section cd at a target CL and trip position]]

**Produced by.** `app/services/turbulator_optimizer_service.py:232` — `optimize_section_xtr`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Area-weighted mean clean section drag` · `cd_clean → cd_tripped fallback` · `Section drag delta`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/schemas/turbulator_optimizer.py:TurbulatorSectionResult.cd_clean` · `frontend/components/workbench/TurbulatorEditDialog.tsx`

**Source.** 🟢 SOURCED

> Sharpe, PhD thesis (MIT, 2024) §7.2.5 (xtr = natural is the un-tripped baseline; 80% of training cases)
>
> — via `aerosandbox-expert`

**The source states it as.**

```
cd_clean = cd(cl, Re) with free transition
```

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:232`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
