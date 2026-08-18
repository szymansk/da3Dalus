---
name: v-v-physical-min
symbol: V_V,min
kind: constant
unit: – (dimensionless)
cluster: stability
user_visible: true
source_status: PARTIAL
---

# V_V physical minimum

**Definition.** Lower bound of physically credible vertical tail volume coefficients.

**Value.** `0.01`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/tail_sizing_service.py:31` — `V_V_PHYSICAL_MIN`

**Consumed by.**

- in this graph: [[tail-volume-classification|Tail volume classification]]
- outside it: `app/services/tail_sizing_service.py:254,284`

**Source.** 🟡 PARTIAL

> Sadraey (Wiley 2013) Table 6.5 (§6.7.1): the lowest tabulated V_V is 0.03 (glider/motor glider); the accompanying text states "Generally V_V ranges from 0.02 to 0.12." No source states 0.01.
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
V̄_V = S_v·l_v/(S·b); general range 0.02–0.12 (Sadraey §6.7.1)
```

**⚠️ Divergence from the source.** The code's floor (0.01) is half the literature floor (0.02). Any aircraft between 0.01 and 0.02 — outside Sadraey's stated general range — passes the 'physical validity' guard.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Sadraey Table 6.5 is a transport/GA/fighter table. No RC/UAV-scale V_V bounds were found in any consulted source, including the RC vault (rcplanedesigner.com sizes the fin by area ratio to the horizontal tail — 35–50 %, rarely beyond 60 % — not by V_V), so this bound has no scale-appropriate basis at all (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** No source (ADR 0023).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
