---
name: alr-cl-max-weight-default
symbol: —
kind: constant
unit: dimensionless
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Mission cl_max_weight default

**Definition.** Weight of the CL_max bonus when a mission weight table omits it.

**Value.** `0.5`

**Formula — as the code writes it.**

```
cl_max_weight = weights.get("cl_max_weight", 0.5)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:915` — `score_mission`

**Consumed by.**

- in this graph: [[alr-cl-bonus|Mission CL_max bonus]]
- outside it: `score_mission:937`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 0.5 fallback weight, no source.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `cl_max_weight = weights.get("cl_max_weight", 0.5)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
