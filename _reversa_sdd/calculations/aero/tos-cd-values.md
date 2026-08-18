---
name: tos-cd-values
symbol: cd_values
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: false
source_status: PARTIAL
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/partial
  - flag/divergence
---

# cd sweep over the trip grid

**Definition.** Array of section cd values, one per xtr grid point, at the section's (cl, Re).

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cd_values = np.array([_cd_at_cl_xtr(airfoil, cl, re, float(xtr)) for xtr in xtr_grid])
```

**Inputs.**

- [[tos-cd-at-cl|Section cd at a target CL and trip position]]
- [[tos-xtr-grid|Turbulator trip-position sweep grid]]

**Produced by.** `app/services/turbulator_optimizer_service.py:210` — `optimize_section_xtr`

**Consumed by.**

- in this graph: `All-NaN sweep guard` · `Tripped section drag` · `Optimal trip position`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟡 PARTIAL

> Sharpe, PhD thesis (MIT, 2024) §7.2.5 (trip location as a model input, so a trip sweep is a legitimate NeuralFoil query pattern)
>
> — via `aerosandbox-expert`

**⚠️ Divergence from the source.** Sweep bookkeeping; no formula to source.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:210`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
