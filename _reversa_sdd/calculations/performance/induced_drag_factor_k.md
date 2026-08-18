---
name: induced_drag_factor_k
symbol: k
kind: quantity
unit: dimensionless
cluster: perf-matching
user_visible: false
source_status: SOURCED
---

# Induced-drag factor

**Definition.** Lift-induced drag coefficient factor 1/(π·e·AR).

**Formula — as the code writes it.**

```
k = 1.0 / (math.pi * e * ar)
```

**Inputs.** [[e_resolved|Resolved Oswald factor]] · [[ar_resolved|Resolved aspect ratio]]

**Produced by.** `app/services/matching_chart_service.py:267` — `_v_md`

**Consumed by.**

- outside it: `_v_md:270` · `_cruise_constraint:373` · `_climb_constraint:411` · `_vertical_climb_constraint:583`

**Source.** 🟢 SOURCED

> Sadraey 2013 Eq. 4.41 §4.3.3.1: K = 1/(pi*e*AR), used with the drag polar C_D = C_Do + K*C_L^2 (Eq. 4.40). Scholz 05_PreliminarySizing §5.7 uses the same grouping (C_L,md = sqrt(pi*A*e*C_D0), Eq. 5.39).
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
K = 1/(pi*e*AR)
```

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
