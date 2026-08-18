---
name: cl_max_to_fl
symbol: CL_max_TO
kind: quantity
unit: dimensionless
cluster: perf-matching
user_visible: false
source_status: PARTIAL
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/partial
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Takeoff CL_max (field length)

**Definition.** CL_max in takeoff configuration, from the polar or from base CL_max times the flap factor.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cl_max_to: float = float(aircraft.get("cl_max_takeoff") or cl_max_base * to_factor)
```

**Inputs.**

- [[cl_max_base_fallback_fl|Base CL_max fallback (field length)]]  — *⤵ fallback*
- [[cl_max_flap_factors_resolved|Resolved flap factors]]  — *⤵ fallback*

**Produced by.** `app/services/field_length_service.py:360` — `compute_field_lengths`

**Consumed by.**

- in this graph: `Takeoff ground roll`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_compute_s_to_ground:424` · `_compute_s_to_bungee_partial:416`

**Source.** 🟡 PARTIAL

> Scholz 05_PreliminarySizing §5.2 Table 5.1 gives CL_max,TO by class (single-engine propeller 1.3-1.9; twin prop 1.4-2.0; business/jet transport 1.6-2.2). Sadraey Eq. 4.69c gives CL_TO = CL_C + CL_flap_TO. The code's route (base * multiplicative flap factor) is not sourced.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
CL_max,TO from class table, or CL_C + dCL_flap,TO (additive)
```

**⚠️ Divergence from the source.** Uses `or`, so a legitimately computed cl_max_takeoff of 0.0 is treated as absent (falsy-vs-None bug, shared with cl_max_landing). Separately, the multiplicative flap route has no basis in either source (see flap_factors).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Table 5.1 covers manned aircraft only; no CL_max,TO band exists in the sources for a 0.5-15 kg low-Re wing.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** `or` treats a legitimately computed cl_max_takeoff of 0.0 as absent — falsy-vs-None bug shared with cl_max_landing.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
