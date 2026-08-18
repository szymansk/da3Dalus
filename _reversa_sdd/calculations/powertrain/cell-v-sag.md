---
name: cell-v-sag
symbol: CELL_V_SAG
kind: constant
unit: V/cell
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/powertrain
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Cell voltage under load

**Definition.** Cell voltage assumed under peak load, used to convert peak power into peak current.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `3.5`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_solution_space_service.py:69` — `CELL_V_SAG`

**Consumed by.**

- in this graph: `Pack voltage under load`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:135`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** RC-Network Wiki 'Nennspannung' states that 'a battery's terminal or open-circuit voltage varies with chemistry, charge state, and load' and gives 3.7 V as the rated value under typical current — but quotes no under-peak-load figure. 3.5 V/cell has no attribution. Note it is also load-independent in the code: it does not depend on the current drawn, the C-rate, or internal resistance, which is precisely what the source says governs the real value.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Magic number with no source: 3.5 V/cell sag is a fixed assumption independent of C-rate, internal resistance, or the current actually drawn — the sag model has no dependence on the load it is modelling. This is also the only place in the cluster that models sag at all (powertrain_performance.py uses 3.7 V throughout).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# V  under peak load — NO_SOURCE_FOUND for the 3.5 value`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
