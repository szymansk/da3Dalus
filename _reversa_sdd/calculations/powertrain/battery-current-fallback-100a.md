---
name: battery-current-fallback-100a
symbol: 100.0
kind: constant
unit: A
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
  - flag/scale
---

# Unknown-battery current fallback

**Definition.** Current assumed when neither the motor current limit nor the battery C-rate is known, so a power ceiling can still be produced.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `100.0`

**Formula — as the code writes it.**

```
battery.max_current_a if not math.isinf(battery.max_current_a) else 100.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_performance.py:657` — `compute_performance_curve`

**Consumed by.**

- in this graph: `Electrical power ceiling`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:653`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Scale (ADR 0023).** 100 A is not a conservative assumption at RC/UAV scale (0.5-15 kg). RC-Network Wiki 'Motorsteller' notes ESCs are historically rated at standard pack capacities and that continuous ratings are the governing figure; a 100 A default silently assumes a powertrain far above the median of this mass class.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Magic number contradicted by the comment above it ("conservative 500 W placeholder"); 100 A is not conservative for a 0.5-15 kg RC/UAV airframe. The accompanying warning text (line 660) says the ceiling was "estimated from battery C-rate only", which is false in exactly the branch that fires it (the C-rate was infinite/unknown).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
