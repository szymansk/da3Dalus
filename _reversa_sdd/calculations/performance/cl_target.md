---
name: cl_target
symbol: CL_target
kind: quantity
unit: dimensionless
cluster: perf-oppoints
user_visible: false
source_status: SOURCED
---

# Target lift coefficient

**Definition.** Lift coefficient the trim must reach for level (or n-g) flight at the target speed.

**Formula — as the code writes it.**

```
q_dyn = 0.5 * rho * max(candidate_velocity_mps, 1e-3) ** 2; if q_dyn <= 1e-6: return None; return float((total_mass_kg * 9.81 * n_target) / (q_dyn * s_ref))
```

**Inputs.** [[effective_mass_kg|Effective aircraft mass]] · [[s_ref|Reference wing area]] · [[air_density_rho|Air density at the operating altitude]] · [[turn_n_target|Turn target load factor]] · [[n_target_level|Level-flight target load factor]] · [[gravity_g|Gravitational acceleration]]

**Produced by.** `app/services/operating_point_generator_service.py:794` — `_cl_target_for_velocity`

**Consumed by.**

- in this graph: [[alr-cd-at-target|CD at target CL]] · [[trim_objective|Opti trim objective]] · [[trim_score|Trim score]]
- outside it: `app/services/operating_point_generator_service.py:676 (objective)` · `app/services/operating_point_generator_service.py:195 (_compute_trim_score)` · `app/services/operating_point_generator_service.py:829 (grid search)`

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §1.5: q∞ = ½ρ∞V∞², C_L = L/(q∞·S). Sadraey §4.3.2, Eq. 4.30: L = W in level flight, generalised to L = n·W in a manoeuvre (Lennon Ch. 21).
>
> — via `aerodynamics-expert, aircraft-design-scholz, rc-aircraft-designer`

**The source states it as.**

```
CL = n·m·g / (0.5·rho·V²·S)
```

**⚠️ Divergence from the source.** Exact match to the sources. This is the best-founded formula in the cluster.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
