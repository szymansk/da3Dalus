---
name: curve-advance-ratio
symbol: J
kind: quantity
unit: dimensionless
cluster: powertrain
user_visible: true
source_status: SOURCED
---

# Advance ratio per velocity sample

**Definition.** Advance ratio at each swept velocity, using whichever RPM the active motor model produced.

**Formula — as the code writes it.**

```
J = V_f / (point_n_rps * D_m) if (point_n_rps > 0 and D_m > 0) else 0.0
```

**Inputs.** [[curve-prop-rpm|Fixed operating RPM (non-QPROP branch)]] · [[qprop-rpm-solution|Solved operating RPM]] · [[curve-diameter-m|Propeller diameter in metres]]

**Produced by.** `app/services/powertrain_performance.py:733` — `compute_performance_curve`

**Consumed by.**

- in this graph: [[polar-extrapolation-warning|Advance-ratio extrapolation flag]] · [[polar-j-clamp|Clamped advance ratio for interpolation]]
- outside it: `app/services/powertrain_performance.py:743` · `app/services/powertrain_performance.py:768`

**Source.** 🟢 SOURCED

> Brandt & Selig, AIAA 2011-1255, §III eqs. 4-7: J = V/(nD).
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
J = V / (n D)
```

**Cited in the code itself.** `docstring step 5a: "J = V / (n·D)"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
