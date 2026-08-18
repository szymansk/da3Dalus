---
name: ss-c-margin
symbol: c_margin
kind: parameter
unit: dimensionless
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-parameter
tags:
  - cluster/powertrain
  - class/unclassified-parameter
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Battery C-rate margin

**Definition.** Safety multiplier applied to the physically required C-rate.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `1.25`

**Formula — as the code writes it.**

```
c_min = raw_c * c_margin
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/schemas/powertrain_solution_space.py:64` — `SolutionSpaceAssumptions.c_margin`

**Consumed by.**

- in this graph: `Required battery C-rate`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:146` · `app/services/powertrain_solution_space_service.py:390`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source in any vault states a battery C-rate safety multiplier. 1.25 is unattributed, and it is applied to the recommended C_min but not to the hyperbola plotted beside it, so the two disagree by exactly this unattributed factor.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Magic number, no source. Applied to c_min but NOT to the plotted hyperbola (line 183), so the chart and the recommendation disagree by exactly this factor.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `field description: "Battery C-rate margin multiplier" — NO_SOURCE_FOUND`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
