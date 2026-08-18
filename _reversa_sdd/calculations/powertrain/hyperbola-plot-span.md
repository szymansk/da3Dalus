---
name: hyperbola-plot-span
symbol: 4.0
kind: constant
unit: dimensionless
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/powertrain
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - flag/divergence
---

# Hyperbola plot span multiplier

**Definition.** How far past the capacity floor the C-rate hyperbola is sampled, purely for plotting room.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `4.0`

**Formula — as the code writes it.**

```
cap_max = cap_floor_mah * 4.0
```

**Inputs.**

- [[ss-cap-mah|Minimum battery capacity]]  — *⊣ limit*

**Produced by.** `app/services/powertrain_solution_space_service.py:181` — `_build_hyperbola`

**Consumed by.**

- in this graph: `Hyperbola capacity samples`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:182`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Plot extent, no engineering content.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `# The x-axis starts at cap_floor_mah and extends to 4× for plotting room.`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
