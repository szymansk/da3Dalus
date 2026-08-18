---
name: v-v-physical-max
symbol: V_V,max
kind: constant
unit: – (dimensionless)
cluster: stability
user_visible: true
source_status: SOURCED
node_class: unclassified-constant
tags:
  - cluster/stability
  - class/unclassified-constant
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# V_V physical maximum

**Definition.** Upper bound of physically credible vertical tail volume coefficients.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.12`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/tail_sizing_service.py:32` — `V_V_PHYSICAL_MAX`

**Consumed by.**

- in this graph: `Tail volume classification`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/tail_sizing_service.py:254,284`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §6.7.1, Table 6.5 and accompanying text: "Generally V_V ranges from 0.02 to 0.12." Highest tabulated entry 0.09 (jet transport).
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
V̄_V = S_v·l_v/(S·b); general range 0.02–0.12
```

**⚠️ Divergence from the source.** The value matches the source's upper bound exactly. Note the code's V_V floor (0.01) does not match the same source's lower bound (0.02) — the pair was not taken consistently from this range.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Table 6.5 covers gliders through jet transports and fighters. At 0.5–15 kg the code's own class targets top out at 0.060 (uav_survey), so the transport-derived ceiling of 0.12 is twice the largest RC/UAV target and will effectively never bind (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** No source (ADR 0023).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
