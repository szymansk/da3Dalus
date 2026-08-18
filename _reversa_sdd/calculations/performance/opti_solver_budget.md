---
name: opti_solver_budget
kind: parameter
unit: mixed (iterations and seconds)
cluster: perf-oppoints
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: WRONG_UNIT
node_class: unclassified-parameter
tags:
  - cluster/perf-oppoints
  - class/unclassified-parameter
  - source/no-source-found
  - audit/wrong-unit
  - flag/anomaly
  - flag/divergence
---

# Opti solver budget

**Definition.** Iteration and wall-clock limits for the IPOPT trim solve.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `max_iter=120, max_runtime=0.35 s`

**Formula — as the code writes it.**

```
solution = opti.solve(verbose=False, max_iter=120, max_runtime=0.35, behavior_on_failure="return_last")
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:685` — `_solve_trim_candidate_with_opti`

🟠 **Corrected by the audit** — the extraction claimed `WRONG_UNIT`. Original unit was `iterations / s`. max_iter in iterations, max_runtime in seconds; unit 'iterations / s' is invalid

**Consumed by.**

- outside it: `app/services/operating_point_generator_service.py:690-701`

**Source.** 🔴 NO SOURCE FOUND

> AeroSandbox Opti reference — solver limits are user parameters, no recommended values published
>
> — via `aerosandbox-expert`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** max_iter=120 / max_runtime=0.35 s are implementation choices with no source. The wall-clock cap combined with behavior_on_failure='return_last' makes the trimmed alpha machine- and load-dependent and returns a non-converged iterate as a solution with no warning (ADR 0020) — a determinism defect, not a provenance gap.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** A 0.35 s wall-clock cap with behavior_on_failure="return_last" makes the trimmed alpha machine- and load-dependent, and a timed-out non-converged iterate is returned as a solution with no warning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
