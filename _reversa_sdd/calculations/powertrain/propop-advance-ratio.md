---
name: propop-advance-ratio
symbol: J
kind: quantity
unit: dimensionless
cluster: powertrain
user_visible: false
source_status: SOURCED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/sourced
---

# Advance ratio (operating point)

**Definition.** Propeller advance ratio V/(n.D) at the given RPM and airspeed; zero if the shaft is stopped or diameter is zero.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if n_rps > 0 and D_m > 0: J = V / (n_rps * D_m) else: J = 0.0
```

**Inputs.**

- [[propop-n-rps|Propeller rotational speed (operating point)]]

**Produced by.** `app/services/powertrain_performance.py:390` — `compute_prop_operating_point`

**Consumed by.**

- outside it: `app/services/powertrain_performance.py:403`

**Source.** 🟢 SOURCED

> Brandt & Selig, AIAA 2011-1255, §III eqs. 4-7: J = V/(nD), V = freestream velocity, n = rev/s, D = propeller diameter. Also Deters/Ananda/Selig 2014 §II.D.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
J = V / (n D)
```

**Cited in the code itself.** `# Advance ratio J = V / (n·D)`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
