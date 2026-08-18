---
name: ss-c-min
symbol: C_min
kind: quantity
unit: 1/h (C)
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Required battery C-rate

**Definition.** C-rate the designer must shop for: the physically required rate multiplied by the safety margin.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
c_min = raw_c * c_margin
```

**Inputs.**

- [[ss-raw-c|Raw required C-rate]]
- [[ss-c-margin|Battery C-rate margin]]

**Produced by.** `app/services/powertrain_solution_space_service.py:146` — `_per_cell`

**Consumed by.**

- in this graph: `Catalog battery match flag`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:426` · `app/services/powertrain_solution_space_service.py:447` · `app/services/powertrain_solution_space_service.py:479` · `frontend/components/workbench/PowertrainTab.tsx:128`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** The raw C-rate is a standard definition (see ss-raw-c), but the 1.25 safety multiplier applied on top of it has no source — see ss-c-margin.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** c_min carries the margin but is compared against catalog c_rating in _catalog_battery_match (line 218), so the catalog flag is a margin-inclusive test while the hyperbola plotted next to it (_build_hyperbola, line 183) is margin-free — the plotted boundary and the match flag use different thresholds.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Required C-rate the designer must shop for: raw physical C × margin.`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
