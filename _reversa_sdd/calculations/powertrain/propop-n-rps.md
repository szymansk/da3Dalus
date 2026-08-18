---
name: propop-n-rps
symbol: n
kind: quantity
unit: 1/s
cluster: powertrain
user_visible: false
source_status: SOURCED
---

# Propeller rotational speed (operating point)

**Definition.** Shaft revolutions per second derived from RPM.

**Formula — as the code writes it.**

```
n_rps = rpm / 60.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_performance.py:386` — `compute_prop_operating_point`

**Consumed by.**

- in this graph: [[propop-advance-ratio|Advance ratio (operating point)]] · [[propop-p-shaft|Propeller shaft power (operating-point helper)]] · [[propop-thrust|Propeller thrust (operating-point helper)]]
- outside it: `app/services/powertrain_performance.py:390` · `app/services/powertrain_performance.py:406` · `app/services/powertrain_performance.py:411`

**Source.** 🟢 SOURCED

> Brandt & Selig, AIAA 2011-1255, §III eqs. 4-7 define n as 'propeller rotational speed (revolutions per second)' throughout the C_T/C_P/J definitions; Sadraey (2013) §8.7, Eq. 8.11 gives the rpm-to-rad/s companion omega = 2*pi*n/60.
>
> — via `rc-aircraft-designer / aircraft-design-scholz`

**The source states it as.**

```
n [rev/s] = RPM / 60
```

**Cited in the code itself.** `# revolutions per second`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
