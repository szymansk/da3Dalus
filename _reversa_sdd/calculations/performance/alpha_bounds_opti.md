---
name: alpha_bounds_opti
kind: parameter
unit: deg
cluster: perf-oppoints
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Opti alpha bounds and initial guess

**Definition.** Search bounds and starting value for the angle of attack in the Opti trim solve.

**Value.** `lower -8.0, init 3.0, upper = max_alpha_deg (default 25.0)`

**Formula — as the code writes it.**

```
alpha_lower = -8.0; alpha_upper = max(alpha_lower + 1.0, max_alpha); alpha_deg = opti.variable(init_guess=min(max(3.0, alpha_lower), alpha_upper), lower_bound=alpha_lower, upper_bound=alpha_upper)
```

**Inputs.** [[default_max_alpha_deg|Default maximum angle of attack]]

**Produced by.** `app/services/operating_point_generator_service.py:597` — `_solve_trim_candidate_with_opti`

**Consumed by.**

- in this graph: [[alpha_trimmed|Trimmed angle of attack]]
- outside it: `app/services/operating_point_generator_service.py:690 (solved_alpha)`

**Source.** 🔴 NO SOURCE FOUND

> Related: Anderson, Fundamentals of Aerodynamics 6e §4.3 — NACA 2412 has α_L=0 = −2.1° and stalls ≈16°; Sadraey §5.4.3 — α_s typically 12–16°
>
> — via `aerodynamics-expert, aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** −8.0° lower bound and 3.0° initial guess have no source. The upper bound inherits max_alpha_deg (default 25°), i.e. ~9° past stall, so the solver may converge to a post-stall alpha where the AeroBuildup polar is least reliable, and the ALPHA_LIMIT_REACHED check (which compares against the same number) can then never fire on the Opti path.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** -8.0 and 3.0 are magic numbers with no cited source.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
