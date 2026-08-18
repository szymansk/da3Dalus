---
name: motor-continuous-current-input
symbol: continuous_current_a
kind: parameter
unit: A
cluster: powertrain
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: unclassified-parameter
tags:
  - cluster/powertrain
  - class/unclassified-parameter
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Motor continuous current rating

**Definition.** Continuous current rating from the catalog.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_performance.py:101` — `MotorSpec.continuous_current_a`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Motor continuous electrical input power (estimated)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:168`

**Source.** 🟢 SOURCED

> RC-Network Wiki, 'Motorsteller': 'The most important specification: maximum continuous current capacity determines controller size and weight.' Roxxy Motoren-Fibel Ch. 3, pp. 28-29 on thermal limits (copper enamel fails above 150 degC).
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
Continuous current rating = the sustained thermal limit
```

**⚠️ Divergence from the source.** The source designates this the most important specification. In the code its only consumer is dead, so the field never influences any result.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Its only consumer (continuous_electrical_power_w) is itself dead, so this catalog field never influences any result.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
