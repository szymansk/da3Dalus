---
name: polar-cp
symbol: Cp
kind: quantity
unit: dimensionless
cluster: powertrain
user_visible: true
source_status: SOURCED
---

# Propeller power coefficient

**Definition.** Power coefficient P/(rho.n^3.D^5) linearly interpolated over J from the polar rows. Not clamped.

**Formula — as the code writes it.**

```
Cp_interp = float(np.interp(J_clamp, Js, Cps))
```

**Inputs.** [[polar-j-clamp|Clamped advance ratio for interpolation]] · [[polar-samples-input|Propeller polar rows]]

**Produced by.** `app/services/powertrain_performance.py:329` — `interpolate_ct_cp_pe`

**Consumed by.**

- in this graph: [[curve-p-shaft|Shaft power per velocity sample]] · [[polar-pe|Propeller efficiency from polar]] · [[prop-torque-demand|Propeller absorbed torque]] · [[propop-p-shaft|Propeller shaft power (operating-point helper)]]
- outside it: `app/services/powertrain_performance.py:335` · `app/services/powertrain_performance.py:336` · `app/services/powertrain_performance.py:411` · `app/services/powertrain_performance.py:467` · `app/services/powertrain_performance.py:756`

**Source.** 🟢 SOURCED

> Brandt & Selig, AIAA 2011-1255, §III, eqs. 4-7: C_P = P / (rho n^3 D^5), where P is the mechanical shaft power input to the propeller.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
C_P = P / (rho * n^3 * D^5)
```

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
