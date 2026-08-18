---
name: motor-cells-lipo-max-input
symbol: cells_lipo_max
kind: parameter
unit: cells (S)
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

# Maximum LiPo cell count

**Definition.** Highest cell count the motor is rated for; used as the voltage basis of the estimated power ceilings.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_performance.py:98` — `MotorSpec.cells_lipo_max`

**Consumed by.**

- in this graph: `Motor continuous electrical input power (estimated)` · `Motor maximum electrical input power (estimated)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:159` · `app/services/powertrain_performance.py:171`

**Source.** 🟢 SOURCED

> Roxxy Motoren-Fibel, Ch. 1, pp. 15-16: 'Exceeding the motor's thermal and mechanical limits by oversizing the battery (e.g. running 6S through a 4S-rated motor) degrades efficiency and longevity.' The cell-count rating is a thermal/mechanical limit.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
Cell count sets the no-load RPM target: RPM = KV x V_bat
```

**⚠️ Divergence from the source.** The source frames cells_lipo_max as a NOT-TO-EXCEED limit. The code uses it as the assumed operating voltage for its power ceilings, i.e. it assumes every motor is always run at its maximum rated cell count regardless of the pack actually selected.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
