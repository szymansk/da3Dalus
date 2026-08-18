---
name: alr-cl-max
symbol: CL_max
kind: quantity
unit: dimensionless
cluster: aero-polars
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/divergence
---

# Section CL_max

**Definition.** Peak lift coefficient over the trusted alpha sweep at one Re.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
idx_max = int(np.argmax(cl_f))
cl_max = float(cl_f[idx_max])
```

**Inputs.**

- [[alr-alpha-sweep|Alpha sweep bounds and step]]  — *⊣ limit*
- [[alr-confidence-gate|NeuralFoil confidence gate]]

**Produced by.** `app/services/airfoil_low_re_service.py:615` — `_extract_metrics`

**Consumed by.**

- in this graph: `Attached-flow alpha window` · `Mission CL_max bonus` · `Match component of score_target_cl` · `re_agnostic suitability score` · `Stall gentleness` · `cl_max_margin`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `AirfoilLowRePolarModel.cl_max` · `score_re_agnostic:849` · `score_mission:897` · `score_target_cl:1043` · `suitability_service:518 (cl_max_margin)`

**Source.** 🟢 SOURCED

> Anderson 6e §4.12.4 — maximum lift coefficient occurs at the stalling angle, the peak of the lift curve
>
> — via `aerodynamics-expert`

**The source states it as.**

```
C_l,max = max_α C_l(α)
```

**⚠️ Divergence from the source.** Same definition. Bounded above by the 18° sweep cap (see alr-alpha-sweep).

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `idx_max = int(np.argmax(cl_f))
cl_max = float(cl_f[idx_max])`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
