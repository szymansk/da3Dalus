---
name: default_approach_speed_margin_vs_ldg
kind: constant
unit: dimensionless
cluster: perf-oppoints
user_visible: true
source_status: SOURCED
node_class: unclassified-constant
tags:
  - cluster/perf-oppoints
  - class/unclassified-constant
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Default approach margin

**Definition.** Multiplier over landing-config stall speed for the approach point.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `1.30`

**Formula — as the code writes it.**

```
"approach_speed_margin_vs_ldg": 1.30
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:208` — `_default_profile`

**Consumed by.**

- in this graph: `approach_landing target speed`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/operating_point_generator_service.py:403`

**Source.** 🟢 SOURCED

> Scholz, Flugzeugentwurf, 05_PreliminarySizing §5.1, citing CS 25.125: landing distance 'determined in landing configuration with stabilised approach at calibrated airspeed not less than 1.3 V_s'. Sadraey §12.4 aileron design example likewise uses V_app = 1.3·V_s.
>
> — via `aircraft-design-scholz, rc-aircraft-designer`

**The source states it as.**

```
V_REF = 1.30 · V_S0
```

**⚠️ Divergence from the source.** Formula form matches exactly.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** CS-25 / FAR-25 is transport-category certification. The RC-scale authority for the same quantity is Lennon Ch. 4, which uses 1.2·V_s for landing speed — the app is 8 % more conservative than RC practice on a 0.5–15 kg aircraft, on the strength of an airliner rule. ADR 0023: adopt with a recorded RC/UAV justification or move to 1.2.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** 1.30 matches the CS/FAR-25 transport-category V_REF = 1.3·V_S0 rule but is applied to a 0.5–15 kg RC/UAV with no source cited (ADR 0023).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
