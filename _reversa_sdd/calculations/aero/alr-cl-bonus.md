---
name: alr-cl-bonus
symbol: —
kind: quantity
unit: dimensionless
cluster: aero-polars
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Mission CL_max bonus

**Definition.** Weighted blend between 1.0 and CL_max/1.5, controlled by the mission's cl_max_weight.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cl_norm = min(cl_max / 1.5, 1.0)
cl_bonus = (1.0 - cl_max_weight) + cl_max_weight * cl_norm
```

**Inputs.**

- [[alr-cl-max|Section CL_max]]  — *⊣ limit*
- [[alr-cl-max-weight-default|Mission cl_max_weight default]]  — *⤵ fallback*

**Produced by.** `app/services/airfoil_low_re_service.py:937` — `score_mission`

**Consumed by.**

- in this graph: `Mission suitability score`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `score_mission:939`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source for the blend. Re-inlines the 1.5 CL_max reference that is separately named CL_MAX_REF at line 856 (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The 1.5 CL_max reference is inlined here and separately named CL_MAX_REF at line 856 — same number, two producers.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `cl_norm = min(cl_max / 1.5, 1.0)
# Weighted interpolation: (1-weight) * 1.0 + weight * cl_norm
cl_bonus = (1.0 - cl_max_weight) + cl_max_weight * cl_norm`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
