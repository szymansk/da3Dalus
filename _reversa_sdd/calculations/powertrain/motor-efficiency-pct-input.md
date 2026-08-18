---
name: motor-efficiency-pct-input
symbol: efficiency_pct
kind: parameter
unit: %
cluster: powertrain
user_visible: true
source_status: SOURCED
node_class: unclassified-parameter
tags:
  - cluster/powertrain
  - class/unclassified-parameter
  - source/sourced
  - surface/user-visible
  - flag/divergence
---

# Datasheet motor efficiency

**Definition.** Combined motor+gearbox efficiency percentage from the datasheet, when the catalog has it.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_performance.py:92` — `MotorSpec.efficiency_pct`

**Consumed by.**

- in this graph: `Motor + gearbox efficiency`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:145` · `app/services/powertrain_performance.py:793`

**Source.** 🟢 SOURCED

> Roxxy Motoren-Fibel, Ch. 3, pp. 28-29: hobby BLDC peak efficiency 75-85%; Drela, 'DC Motor / Propeller Matching', §1.2 for the definition eta_m = P_shaft/(V I).
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
eta_m = P_shaft/(V I)
```

**⚠️ Divergence from the source.** A datasheet efficiency percentage is a single operating point (the source says peak efficiency sits 'roughly in the center of the motor's operating range' at a power 'significantly lower than the rated power'). The code treats it as constant over the whole sweep.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
