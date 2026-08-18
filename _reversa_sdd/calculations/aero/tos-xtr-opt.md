---
name: tos-xtr-opt
symbol: xtr_opt
kind: quantity
unit: x/c
cluster: aero-strips
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/divergence
---

# Optimal trip position

**Definition.** Trip position x/c that minimises section cd over the sweep grid.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
i_opt = finite_indices[int(np.argmin(cd_values[finite_mask]))]; xtr_opt = float(xtr_grid[i_opt])
```

**Inputs.**

- [[tos-cd-values|cd sweep over the trip grid]]
- [[tos-xtr-grid|Turbulator trip-position sweep grid]]

**Produced by.** `app/services/turbulator_optimizer_service.py:257` — `optimize_section_xtr`

**Consumed by.**

- in this graph: `Grid-boundary minimum warning` · `Tripped section drag`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/schemas/turbulator_optimizer.py:TurbulatorSectionResult.xtr_opt` · `frontend/components/workbench/TurbulatorEditDialog.tsx:209-215`

**Source.** 🟡 PARTIAL

> RC-Network Wiki, 'Turbulator (Aerodynamik)': 'turbulators must be placed at the location where natural transition would otherwise be delayed'; Anderson, Fundamentals of Aerodynamics 6e, §4.12.3-4.12.4 (transition location governs skin friction and separation)
>
> — via `rc-aircraft-designer, aerodynamics-expert`

**The source states it as.**

```
Optimum trip position = where forcing transition suppresses separation at least friction cost
```

**⚠️ Divergence from the source.** The OBJECTIVE (minimise section cd over trip position) matches the cited purpose. The METHOD (exhaustive 15-point grid search, no refinement, minimum taken at grid resolution) is unattributable, and the returned optimum is quantised to 0.05 c.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:255-257`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
