---
name: sui-target-cl-cruise
symbol: CL_cruise
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

# target_cl_cruise

**Definition.** Level-flight CL at the aeroplane's cruise speed; drives ranking when no mission is resolved.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
effective_target_cl_cruise = _level_flight_cl(mass_kg, v_cruise_mps, s_ref_m2)
```

**Inputs.**

- [[alr-level-flight-cl|Level-flight lift coefficient]]

**Produced by.** `app/services/suitability_service.py:336` — `search_suitability`

**Consumed by.**

- in this graph: `cl_max_margin`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `score_target_cl:487` · `SuitabilityQuery.target_cl_cruise:691` · `cl_max_margin:523`

**Source.** 🟢 SOURCED

> Anderson 6e §1.5 (C_L = L/(q∞S)) with steady level flight L = W
>
> — via `aerodynamics-expert`

**The source states it as.**

```
C_L = mg/(½ρV²S)
```

**⚠️ Divergence from the source.** None beyond the ISA-SL density assumption inherited from alr-level-flight-cl.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `effective_target_cl_cruise = _level_flight_cl(
    mass_kg, v_cruise_mps, s_ref_m2
)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
