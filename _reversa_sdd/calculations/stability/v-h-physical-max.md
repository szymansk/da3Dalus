---
name: v-h-physical-max
symbol: V_H,max
kind: constant
unit: – (dimensionless)
cluster: stability
user_visible: true
source_status: PARTIAL
node_class: unclassified-constant
tags:
  - cluster/stability
  - class/unclassified-constant
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# V_H physical maximum

**Definition.** Upper bound of physically credible horizontal tail volume coefficients.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `1.20`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/tail_sizing_service.py:30` — `V_H_PHYSICAL_MAX`

**Consumed by.**

- in this graph: `Tail volume classification`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/tail_sizing_service.py:248,268`

**Source.** 🟡 PARTIAL

> Sadraey (Wiley 2013) Table 6.4 (§6.7.1) tops out at V_H = 1.1 (jet transport); the Klausur SS19 §1.14 material cites V_H ≈ 0.80–1.10 for transports depending on layout (T-tail 0.90–1.10). No source states 1.20.
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
V̄_H = S_h·l_h/(S·C̄); tabulated maximum 1.1 (jet transport, Sadraey Table 6.4)
```

**⚠️ Divergence from the source.** 1.20 is just above the highest tabulated value in the literature, so it functions as a loose sanity ceiling rather than a validated bound — but it is unattributed.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** The value it approximates (1.1) is the jet-transport entry of Sadraey Table 6.4. For 0.5–15 kg RC/UAV aircraft the relevant ceiling is far lower — rcplanedesigner.com's highest RC mission maximum is 0.75 (Trainer), and Lennon Ch. 7's reference case implies V_H ≈ 0.50. Adopting a transport ceiling means no RC design can ever trip this guard (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** No source (ADR 0023).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
