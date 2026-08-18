---
name: polar-extrapolation-warning
symbol: extrapolation_warning
kind: quantity
unit: boolean
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/no-source-found
  - surface/user-visible
---

# Advance-ratio extrapolation flag

**Definition.** True when the requested J fell outside the polar dataset range, meaning the returned coefficients are held at the boundary value.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
extrapolation_warning = (J < J_min) or (J > J_max)
```

**Inputs.**

- [[curve-advance-ratio|Advance ratio per velocity sample]]

**Produced by.** `app/services/powertrain_performance.py:323` — `interpolate_ct_cp_pe`

**Consumed by.**

- outside it: `app/services/powertrain_performance.py:744` · `app/services/powertrain_performance.py:774`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**Cited in the code itself.** `module docstring: "Extrapolation beyond the dataset J-range emits a warning."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
