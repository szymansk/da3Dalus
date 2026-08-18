---
name: tos-cd-tripped
symbol: cd_tripped
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

# Tripped section drag

**Definition.** Section cd at the optimal trip position.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cd_tripped = float(cd_values[i_opt])
```

**Inputs.**

- [[tos-cd-values|cd sweep over the trip grid]]
- [[tos-xtr-opt|Optimal trip position]]

**Produced by.** `app/services/turbulator_optimizer_service.py:258` — `optimize_section_xtr`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `cd_clean → cd_tripped fallback` · `Section drag delta`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/schemas/turbulator_optimizer.py:TurbulatorSectionResult.cd_tripped`

**Source.** 🟢 SOURCED

> Sharpe, PhD thesis (MIT, 2024) §7.2.5 (forced trip x_tr as a NeuralFoil input)
>
> — via `aerosandbox-expert`

**The source states it as.**

```
cd_tripped = cd(cl, Re; xtr_upper = xtr_opt)
```

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:258`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
