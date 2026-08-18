---
name: cl_max_l_mc
symbol: CL_max_LDG
kind: parameter
unit: dimensionless
cluster: perf-matching
user_visible: false
source_status: PARTIAL
node_class: unclassified-parameter
tags:
  - cluster/perf-matching
  - class/unclassified-parameter
  - source/partial
  - flag/divergence
  - flag/scale
---

# Landing CL_max (matching chart)

**Definition.** Landing CL_max for the landing constraint, defaulting to the clean value.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Formula — as the code writes it.**

```
cl_max_l: float = float(aircraft.get("cl_max_landing", cl_max_clean))
```

**Inputs.**

- [[cl_max_clean_mc|Clean CL_max (matching chart)]]  — *⊣ limit*

**Produced by.** `app/services/matching_chart_service.py:809` — `compute_chart`

**Consumed by.**

- in this graph: `Landing constraint W/S_max`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_landing_constraint:850` · `hover_text:909`

**Source.** 🟡 PARTIAL

> Scholz 05_PreliminarySizing §5.1 Table 5.1: CL_max,L single-engine propeller 1.6-2.3, twin prop 1.6-2.5. Sadraey Tables 4.10/4.11. Defaulting to the clean value is not sourced and is non-conservative for the landing constraint.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
CL_max,L from class tables / Scholz Figs 5.3-5.4 by high-lift system
```

**⚠️ Divergence from the source.** Defaulting CL_max,L = CL_max_clean removes all high-lift benefit from the landing W/S limit, whereas the endpoint's parallel path applies a hardcoded 1.3x. The two paths disagree by 30% on a user-visible constraint (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Manned-aircraft class table.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
