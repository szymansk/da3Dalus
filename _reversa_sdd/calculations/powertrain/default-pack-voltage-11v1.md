---
name: default-pack-voltage-11v1
symbol: 11.1
kind: constant
unit: V
cluster: powertrain
user_visible: true
source_status: PARTIAL
node_class: unclassified-constant
tags:
  - cluster/powertrain
  - class/unclassified-constant
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Default pack voltage

**Definition.** 3S nominal pack voltage assumed when a battery catalog entry carries no voltage and no cell count.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `11.1`

**Formula — as the code writes it.**

```
if voltage is None: voltage = 11.1
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_sizing_service.py:228` — `_evaluate_motor_battery_combo`

**Consumed by.**

- in this graph: `Resolved battery voltage (sizing)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_sizing_service.py:251`

**Source.** 🟡 PARTIAL

> RC-Network Wiki, 'Nennspannung' gives 11.1 V only as the worked example of a 3-cell pack ('3 x 3.7 = 11.1 V'), not as a default for packs of unknown configuration.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
3S pack rated voltage = 3 x 3.7 = 11.1 V
```

**⚠️ Divergence from the source.** The value is arithmetically the source's 3S example, but using it as the fallback for a battery with no voltage AND no cell count asserts a 3S configuration that nothing in the data supports.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Magic number, silent fallback, no warning.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
