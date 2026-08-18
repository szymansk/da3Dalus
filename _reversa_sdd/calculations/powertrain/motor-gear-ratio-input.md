---
name: motor-gear-ratio-input
symbol: gear_ratio
kind: parameter
unit: dimensionless
cluster: powertrain
user_visible: true
source_status: SOURCED
---

# Gearbox reduction ratio

**Definition.** Gearbox reduction between motor and propeller shaft; absent means direct drive (treated as 1.0).

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_performance.py:91` — `MotorSpec.gear_ratio`

**Consumed by.**

- in this graph: [[motor-output-kv|Output-shaft KV]]
- outside it: `app/services/powertrain_performance.py:140`

**Source.** 🟢 SOURCED

> Sadraey (2013), §8.7, Eq. 8.14: GR = n_P / n_S — 'A gearbox is often used to step the engine shaft speed n_S down to a propeller speed n_P that keeps tip speed below limits.' Worked: Cessna 172 GR = 1/2 (4200 rpm shaft -> 2100 rpm prop).
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
GR = n_P / n_S  (Eq. 8.14)
```

**⚠️ Divergence from the source.** Sadraey's GR is prop-speed over shaft-speed (a fraction < 1 for a reduction gearbox). The code's gear_ratio is the reciprocal (it divides KV by it). Opposite convention for the same physical quantity.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
