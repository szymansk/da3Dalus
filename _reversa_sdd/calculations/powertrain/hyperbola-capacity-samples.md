---
name: hyperbola-capacity-samples
symbol: capacity_curve_mah
kind: quantity
unit: mAh
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Hyperbola capacity samples

**Definition.** Capacity abscissae of the feasible-region boundary curve, linearly spaced from the floor to 4x the floor.

**Formula — as the code writes it.**

```
caps = [cap_floor_mah + (cap_max - cap_floor_mah) * i / (n - 1) for i in range(n)]
```

**Inputs.** [[ss-cap-mah|Minimum battery capacity]] · [[hyperbola-plot-span|Hyperbola plot span multiplier]] · [[hyperbola-samples|C-rate hyperbola sample count]]

**Produced by.** `app/services/powertrain_solution_space_service.py:182` — `_build_hyperbola`

**Consumed by.**

- in this graph: [[hyperbola-c-rate-samples|Hyperbola C-rate samples]]
- outside it: `app/services/powertrain_solution_space_service.py:470` · `frontend/components/workbench/PowertrainTab.tsx:149`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Plot sampling, no engineering content.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** n - 1 in the denominator divides by zero if _HYPERBOLA_SAMPLES were ever set to 1; the parameter n is exposed as a keyword argument with no lower-bound guard.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
