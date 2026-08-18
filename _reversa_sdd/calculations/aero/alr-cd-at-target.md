---
name: alr-cd-at-target
symbol: CD(CL_t)
kind: quantity
unit: dimensionless
cluster: aero-polars
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/partial
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# CD at target CL

**Definition.** Section drag coefficient at the operating CL from the fitted parabolic polar.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cd_at_target = cd0 + k * (cl_target - cl0) ** 2
```

**Inputs.**

- [[alr-polar-cd0|Airfoil cd0 (parabolic fit vertex)]]
- [[alr-polar-k|Airfoil polar curvature k]]
- [[alr-polar-cl0|CL at minimum drag (cl0)]]
- [[cl_target|Target lift coefficient]]

**Produced by.** `app/services/airfoil_low_re_service.py:1045` — `score_target_cl`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Relative drag-rise ratio r`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `score_target_cl:1046`

**Source.** 🟡 PARTIAL

> Anderson 6e §6.7.2 — evaluating the fitted parabolic polar at an operating C_L
>
> — via `aerodynamics-expert`

**The source states it as.**

```
C_D(C_L) = C_D0 + k(C_L − C_L0)²
```

**⚠️ Divergence from the source.** Same form as the fit. Evaluated without checking cl_valid_lo/cl_valid_hi, so for a target CL outside the fitted range the parabola is extrapolated — the stored validity window exists but is never consulted.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Evaluated without checking cl_valid_lo/cl_valid_hi — extrapolates the parabola beyond the fitted range.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `cd_at_target = cd0 + k * (cl_target - cl0) ** 2`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
