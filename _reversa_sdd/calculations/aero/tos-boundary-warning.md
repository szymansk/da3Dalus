---
name: tos-boundary-warning
symbol: —
kind: quantity
unit: n/a
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

# Grid-boundary minimum warning

**Definition.** Warning emitted when the optimum falls on the first or last grid point.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if i_opt == 0 or i_opt == len(xtr_grid) - 1: warnings.append(…)
```

**Inputs.**

- [[tos-xtr-opt|Optimal trip position]]

**Produced by.** `app/services/turbulator_optimizer_service.py:263` — `optimize_section_xtr`

**Consumed by.**

- outside it: `frontend/components/workbench/TurbulatorEditDialog.tsx:342-348`

**Source.** 🟡 PARTIAL


**⚠️ Divergence from the source.** Standard numerical hygiene for a bounded grid search — a minimum on the boundary means the true optimum may lie outside. Correctly declared; no external source needed. The hardcoded '[0.2, 0.9]' in the message text is the defect.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:263-268`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
