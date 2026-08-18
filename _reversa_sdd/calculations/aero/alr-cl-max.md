---
name: alr-cl-max
symbol: CL_max
kind: quantity
unit: dimensionless
cluster: aero-polars
user_visible: true
source_status: SOURCED
---

# Section CL_max

**Definition.** Peak lift coefficient over the trusted alpha sweep at one Re.

**Formula — as the code writes it.**

```
idx_max = int(np.argmax(cl_f))
cl_max = float(cl_f[idx_max])
```

**Inputs.** [[alr-alpha-sweep|Alpha sweep bounds and step]] · [[alr-confidence-gate|NeuralFoil confidence gate]]

**Produced by.** `app/services/airfoil_low_re_service.py:615` — `_extract_metrics`

**Consumed by.**

- in this graph: [[alr-alpha-attached-window|Attached-flow alpha window]] · [[alr-cl-bonus|Mission CL_max bonus]] · [[alr-match|Match component of score_target_cl]] · [[alr-score-re-agnostic|re_agnostic suitability score]] · [[alr-stall-gentleness|Stall gentleness]] · [[sui-cl-max-margin|cl_max_margin]]
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
