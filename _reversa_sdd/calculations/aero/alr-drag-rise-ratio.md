---
name: alr-drag-rise-ratio
symbol: r
kind: quantity
unit: dimensionless
cluster: aero-polars
user_visible: false
source_status: PARTIAL
---

# Relative drag-rise ratio r

**Definition.** Ratio of CD at the target CL to cd0.

**Formula — as the code writes it.**

```
r = cd_at_target / cd0  # relative drag rise; r=1 at CL_min, r>1 away from it
```

**Inputs.** [[alr-cd-at-target|CD at target CL]] · [[alr-polar-cd0|Airfoil cd0 (parabolic fit vertex)]]

**Produced by.** `app/services/airfoil_low_re_service.py:1046` — `score_target_cl`

**Consumed by.**

- in this graph: [[alr-match|Match component of score_target_cl]]
- outside it: `score_target_cl:1052,1055,1071`

**Source.** 🟡 PARTIAL

> Abbott & von Doenhoff (1959), Ch. 6 — drag rise away from the design C_l is the defining behaviour of the low-drag range
>
> — via `aerodynamics-expert`

**⚠️ Divergence from the source.** Normalising by cd0 (the parabola vertex) is a reasonable dimensionless statement of that idea, but no source expresses the drag rise as this ratio.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `r = cd_at_target / cd0  # relative drag rise; r=1 at CL_min, r>1 away from it`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
