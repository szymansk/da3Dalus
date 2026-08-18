---
name: cl_target_guards
kind: constant
unit: m/s and Pa
cluster: perf-oppoints
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: WRONG_LINE
node_class: unclassified-constant
tags:
  - cluster/perf-oppoints
  - class/unclassified-constant
  - source/no-source-found
  - audit/wrong-line
  - flag/divergence
---

# CL-target numerical guards

**Definition.** Velocity floor and dynamic-pressure floor guarding the CL_target division.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `1e-3 m/s, 1e-6 Pa`

**Formula — as the code writes it.**

```
q_dyn = 0.5 * rho * max(candidate_velocity_mps, 1e-3) ** 2; if q_dyn <= 1e-6: return None
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:792` — `_cl_target_for_velocity`

🟠 **Corrected by the audit** — the extraction claimed `WRONG_LINE`. Original line was `794`. Guard conditions on lines 792 and 795-796, not 794

**Consumed by.**

- outside it: `app/services/operating_point_generator_service.py:797`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 1e-3 m/s velocity floor and 1e-6 Pa dynamic-pressure floor are division-by-zero guards. Numerical, not engineering; no source needed. Note the velocity floor is silent — a target velocity of 0 becomes 1e-3 m/s and yields an astronomically large CL_target rather than an error.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
