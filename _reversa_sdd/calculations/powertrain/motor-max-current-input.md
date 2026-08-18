---
name: motor-max-current-input
symbol: max_current_a
kind: parameter
unit: A
cluster: powertrain
user_visible: true
source_status: SOURCED
---

# Motor burst current limit

**Definition.** Burst current limit from the catalog; drives the estimated power ceiling and the QPROP back-EMF floor.

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_performance.py:100` — `MotorSpec.max_current_a`

**Consumed by.**

- in this graph: [[motor-continuous-electrical-power|Motor continuous electrical input power (estimated)]] · [[motor-max-electrical-power|Motor maximum electrical input power (estimated)]] · [[qprop-back-emf-floor|Back-EMF floor at the current ceiling]]
- outside it: `app/services/powertrain_performance.py:159` · `app/services/powertrain_performance.py:704` · `app/services/powertrain_performance.py:548`

**Source.** 🟢 SOURCED

> RC-Network Wiki, 'Motorsteller': 'Reputable manufacturers rate continuous capacity ... Cheap imports sometimes advertise peak (pulse) capacity, which is substantially higher than continuous rating.' Roxxy Motoren-Fibel Ch. 3, pp. 28-29: 'careful attention to continuous vs. burst power ratings are critical in aircraft design.'
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
Continuous rating governs sustained operation; burst/pulse rating is substantially higher
```

**⚠️ Divergence from the source.** Both sources warn that burst and continuous ratings are different quantities and that continuous governs sustained flight. The code applies the BURST current as the ceiling across a whole velocity sweep representing sustained level flight.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Used as the QPROP current ceiling (i_ceiling, line 704) even though it is a BURST rating, applied uniformly across a whole velocity sweep that represents sustained flight.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
