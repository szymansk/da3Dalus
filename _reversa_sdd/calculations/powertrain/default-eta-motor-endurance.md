---
name: default-eta-motor-endurance
symbol: DEFAULT_ETA_MOTOR
kind: constant
unit: dimensionless (0..1)
cluster: powertrain
user_visible: true
source_status: SOURCED
node_class: unclassified-constant
tags:
  - cluster/powertrain
  - class/unclassified-constant
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Default motor efficiency (sizing path)

**Definition.** Flat motor efficiency used by the sizing sweep when the request does not override it.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.85`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/endurance_service.py:54` — `DEFAULT_ETA_MOTOR`

**Consumed by.**

- in this graph: `Combo total propulsive efficiency`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_sizing_service.py:236`

**Source.** 🟢 SOURCED

> Roxxy Motoren-Fibel, Ch. 3, pp. 28-29: 'For typical hobby BLDC motors, peak efficiency typically falls between 75-85% in the flight-typical operating range. Roxxy motors achieve high efficiency levels of 80-85%.'
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
eta_m,peak = 0.75-0.85 for hobby BLDC motors
```

**⚠️ Divergence from the source.** 0.85 is the very top of the cited band and is a PEAK figure. The source adds that 'the point of maximum efficiency lies roughly in the center of the motor's operating range, though actual power output at maximum efficiency is significantly lower than the rated power' — so applying 0.85 at the cruise point of an arbitrary motor is the optimistic end of the source's range, not its centre.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** One of four independent 0.85 literals (notes F3).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Brushless outrunner`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
