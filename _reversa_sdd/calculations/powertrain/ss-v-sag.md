---
name: ss-v-sag
symbol: V_sag
kind: quantity
unit: V
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

# Pack voltage under load

**Definition.** Pack voltage assumed at peak current draw for a candidate cell count.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
v_sag = s * CELL_V_SAG
```

**Inputs.**

- [[cell-v-sag|Cell voltage under load]]
- [[ss-cell-counts|Evaluated cell counts]]

**Produced by.** `app/services/powertrain_solution_space_service.py:135` — `_per_cell`

**Consumed by.**

- in this graph: `Peak battery current`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:140`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Derives from cell-v-sag = 3.5 V, which has no attribution in any vault. RC-Network Wiki 'Nennspannung' says the loaded voltage depends on 'chemistry, charge state, and load' but gives no under-load figure.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Returned as SolutionRow.v_sag_v but never rendered by the UI (notes F6).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `schema: "Pack voltage under load [V] = S × 3.5"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
