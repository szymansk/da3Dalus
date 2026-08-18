---
name: sui-target-cl-best-glide
symbol: CL_md
kind: quantity
unit: dimensionless
cluster: aero-polars
user_visible: true
source_status: SOURCED
---

# target_cl_best_glide

**Definition.** Level-flight CL at V_md (best L/D speed); display-only, never ranks.

**Formula — as the code writes it.**

```
effective_target_cl_best_glide = _level_flight_cl(mass_kg, v_md_mps, s_ref_m2)
```

**Inputs.** [[alr-level-flight-cl|Level-flight lift coefficient]]

**Produced by.** `app/services/suitability_service.py:346` — `search_suitability`

**Consumed by.**

- in this graph: [[sui-cl-max-margin|cl_max_margin]]
- outside it: `score_target_cl:496` · `SuitabilityQuery.target_cl_best_glide:692` · `cl_max_margin:525`

**Source.** 🟢 SOURCED

> Anderson 6e §1.5 (level-flight C_L) and §6.7.2 (best glide occurs at (L/D)_max, i.e. at V_md)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
C_L = mg/(½ρV_md²S)
```

**⚠️ Divergence from the source.** The CL formula is exact. V_md itself is produced elsewhere and is not sourced by this cluster.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `effective_target_cl_best_glide = _level_flight_cl(
    mass_kg, v_md_mps, s_ref_m2
)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
