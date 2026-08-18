---
name: sui-target-cl-min-sink
symbol: CL_min_sink
kind: quantity
unit: dimensionless
cluster: aero-polars
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/divergence
---

# target_cl_min_sink

**Definition.** Level-flight CL at V_min_sink; display-only, never ranks.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
effective_target_cl_min_sink = _level_flight_cl(mass_kg, v_min_sink_mps, s_ref_m2)
```

**Inputs.**

- [[alr-level-flight-cl|Level-flight lift coefficient]]

**Produced by.** `app/services/suitability_service.py:356` — `search_suitability`

**Consumed by.**

- in this graph: `cl_max_margin`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `score_target_cl:505` · `SuitabilityQuery.target_cl_min_sink:693` · `cl_max_margin:526`

**Source.** 🟡 PARTIAL

> Anderson 6e §1.5 — level-flight C_L formula
>
> — via `aerodynamics-expert`

**The source states it as.**

```
C_L = mg/(½ρV²S)
```

**⚠️ Divergence from the source.** The CL evaluation is exact; the minimum-sink condition that produces V_min_sink (C_L = √3 · C_L at best glide for a parabolic polar) is a separate result produced in another cluster and is not sourced here.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `effective_target_cl_min_sink = _level_flight_cl(
    mass_kg, v_min_sink_mps, s_ref_m2
)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
