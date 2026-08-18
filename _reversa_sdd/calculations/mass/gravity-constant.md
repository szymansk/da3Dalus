---
name: gravity-constant
symbol: g
kind: constant
unit: m/s²
cluster: mass
user_visible: false
source_status: SOURCED
---

# Gravitational acceleration

**Definition.** Standard gravity used to convert mass to weight in every speed formula in this module.

**Value.** `9.81`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/assumption_compute_service.py:1763` — `_stall_speed default argument (repeated at :1804, :1871, :1923, :1953, :1978)`

**Consumed by.**

- in this graph: [[weight-force-n|Weight force]]
- outside it: `app/services/assumption_compute_service.py:1774` · `app/services/assumption_compute_service.py:1846 (landing ground roll)` · `app/services/assumption_compute_service.py:1901` · `app/services/assumption_compute_service.py:1942` · `app/services/assumption_compute_service.py:1968`

**Source.** 🟢 SOURCED

> Sadraey, M.H., "Aircraft Design: A Systems Engineering Approach", Wiley 2013, §10.4, sub-section 'Units': "The gravitational constant g = 9.81 m/s² (or 32.17 ft/s²) appears explicitly, converting from mass units to weight (force) units." Independently used as g = 9.81 m/s² in Scholz, D., "Flugzeugentwurf" (HAW Hamburg) worked example 'Wing Loading at Landing'.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
g = 9.81 m/s²
```

**⚠️ Divergence from the source.** Value matches the source exactly. Divergence is only in bookkeeping: seven independent copies of the literal exist (six default arguments in assumption_compute_service.py at :1763, :1804, :1871, :1923, :1953, :1978, plus GRAVITY = 9.81 in mass_cg_service.py:20) where the sources use one named constant.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Six independent default-argument copies of 9.81 in this file, plus a seventh authority GRAVITY = 9.81 in app/services/mass_cg_service.py:20. No single constant module.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
