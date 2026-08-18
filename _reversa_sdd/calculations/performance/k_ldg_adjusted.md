---
name: k_ldg_adjusted
symbol: K_LDG_adj
kind: quantity
unit: dimensionless
cluster: perf-matching
user_visible: false
source_status: PARTIAL
---

# Friction-adjusted landing coefficient

**Definition.** Base landing coefficient rescaled by the ratio of hard-runway to actual braking friction.

**Formula — as the code writes it.**

```
k_ldg = _K_LDG_HARD * (_MU_BRAKE_HARD / mu_brake)
```

**Inputs.** [[k_ldg_hard|Landing ground-roll coefficient]] · [[mu_brake_hard|Braking friction, hard runway]] · [[mu_brake_selected|Selected braking friction]]

**Produced by.** `app/services/field_length_service.py:263` — `_compute_s_ldg_ground`

**Consumed by.**

- in this graph: [[s_ldg_ground|Landing ground roll]]
- outside it: `s_ldg_ground:264`

**Source.** 🟡 PARTIAL

> The 1/mu dependence is correct and follows from s_ground = V_TD^2/(2*mu*g) (Scholz exam-matching-chart-design-point, a_braking; same relation underlying Sadraey §4.3.2).
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
s_ground proportional to 1/mu_brake
```

**⚠️ Divergence from the source.** The scaling itself is right, but it is applied to a fitted constant rather than to a derived one. Since K_LDG_HARD = 0.5847 does not equal k^2/(mu*g) at mu = 0.4 (correct value 0.4307), rescaling by mu_hard/mu propagates the Cessna fit into every non-standard surface instead of removing it.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `"K_LDG_adjusted = K_LDG_HARD · (μ_BRAKE_HARD / μ_brake). This correctly shortens the distance for belly landing (higher μ = 0.5) and keeps the Cessna 172N cross-check valid at μ = 0.4."`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
