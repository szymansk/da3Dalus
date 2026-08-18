---
name: tos-delta-cd
symbol: delta_cd
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/divergence
---

# Section drag delta

**Definition.** Change in section cd caused by tripping at xtr_opt.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
delta_cd = cd_tripped - cd_clean
```

**Inputs.**

- [[tos-cd-tripped|Tripped section drag]]
- [[tos-cd-clean|Natural-transition section drag]]

**Produced by.** `app/services/turbulator_optimizer_service.py:273` — `optimize_section_xtr`

**Consumed by.**

- in this graph: `Area-weighted 3D drag increment`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/schemas/turbulator_optimizer.py:TurbulatorSectionResult.delta_cd`

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §4.12-4.12.3 (profile drag is set by the transition location; turbulent wall shear far exceeds laminar at the same Re, but turbulent boundary layers resist separation); RC-Network Wiki, 'Turbulator': 'better turbulent and attached than laminar and separated'
>
> — via `aerodynamics-expert, rc-aircraft-designer`

**The source states it as.**

```
delta_cd = cd(x_tr forced) - cd(x_tr natural)
```

**⚠️ Divergence from the source.** Exactly the physical definition of a turbulator's effect. Sign convention is worth stating in the API: a BENEFICIAL turbulator gives delta_cd < 0.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:273`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
