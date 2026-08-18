---
name: cl_max_ldg_fl
symbol: CL_max_LDG
kind: quantity
unit: dimensionless
cluster: perf-matching
user_visible: false
source_status: PARTIAL
---

# Landing CL_max (field length)

**Definition.** CL_max in landing configuration, from the polar or from base CL_max times the flap factor.

**Formula — as the code writes it.**

```
cl_max_ldg: float = float(aircraft.get("cl_max_landing") or cl_max_base * ldg_factor)
```

**Inputs.** [[cl_max_base_fallback_fl|Base CL_max fallback (field length)]] · [[cl_max_flap_factors_resolved|Resolved flap factors]]

**Produced by.** `app/services/field_length_service.py:361` — `compute_field_lengths`

**Consumed by.**

- in this graph: [[s_ldg_ground|Landing ground roll]]
- outside it: `_compute_s_ldg_ground:435`

**Source.** 🟡 PARTIAL

> Scholz 05_PreliminarySizing §5.1 Table 5.1: CL_max,L single-engine propeller 1.6-2.3, twin prop 1.6-2.5, jet transport 1.8-2.8. Sadraey Tables 4.10/4.11 by class. The multiplicative derivation from a base CL_max is not sourced.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
CL_max,L selected from empirical class tables / Figs 5.3-5.4 by high-lift system
```

**⚠️ Divergence from the source.** Same falsy-vs-None `or` bug as cl_max_to_fl. Also: the matching-chart endpoint independently computes cl_max_landing = cl_max * 1.3, bypassing this table entirely - two policies for one user-visible quantity (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Manned-aircraft tables only.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
