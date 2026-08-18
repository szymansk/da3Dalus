---
name: tos-cd-clean
symbol: cd_clean
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: true
source_status: SOURCED
---

# Natural-transition section drag

**Definition.** Section cd with no turbulator, evaluated at xtr_upper = 1.0.

**Formula — as the code writes it.**

```
cd_clean = _cd_at_cl_xtr(airfoil, cl, re, xtr_upper=1.0)
```

**Inputs.** [[tos-cd-at-cl|Section cd at a target CL and trip position]]

**Produced by.** `app/services/turbulator_optimizer_service.py:232` — `optimize_section_xtr`

**Consumed by.**

- in this graph: [[tos-cd-clean-avg|Area-weighted mean clean section drag]] · [[tos-cd-clean-nan-fallback|cd_clean → cd_tripped fallback]] · [[tos-delta-cd|Section drag delta]]
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
