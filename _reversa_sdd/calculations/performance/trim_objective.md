---
name: trim_objective
kind: quantity
unit: dimensionless
cluster: perf-oppoints
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: derived
tags:
  - cluster/perf-oppoints
  - class/derived
  - source/no-source-found
  - flag/anomaly
  - flag/divergence
---

# Opti trim objective

**Definition.** Weighted least-squares objective minimised by the trim solver.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
objective = 50.0 * cm**2 + 3.0 * cy**2; if cl_target is not None: objective += 15.0 * (cl - cl_target) ** 2; if target["name"].startswith("turn_"): objective += 2.0 * result["Cl"] ** 2 + 2.0 * result["Cn"] ** 2; for control in control_variables.values(): objective += 0.001 * control**2
```

**Inputs.**

- [[cl_target|Target lift coefficient]]

**Produced by.** `app/services/operating_point_generator_service.py:674` — `_solve_trim_candidate_with_opti`

**Consumed by.**

- in this graph: `Trimmed angle of attack`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/operating_point_generator_service.py:682 (opti.minimize)`

**Source.** 🔴 NO SOURCE FOUND

> The trim CONDITION is sourced — Sadraey §12.5: longitudinal trim is ΣM_cg = 0, i.e. Cm = 0 — but no weighting of a multi-residual objective appears in any consulted source.
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** All six weights (50, 3, 15, 2, 2, 0.001) are numerical-tuning constants with no engineering provenance. Compounding finding: this objective (Cm²:CY²:ΔCL² = 50:3:15) is inconsistent with _compute_trim_score (\|Cm\|:\|CY\|:\|ΔCL\| = 1:0.5:0.3), which then judges the same solution — the solver optimises one metric and is graded on another.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Six unsourced weights (50, 3, 15, 2, 2, 0.001) that are inconsistent with the 1 / 0.5 / 0.3 weighting of _compute_trim_score, which then judges the same solution.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
