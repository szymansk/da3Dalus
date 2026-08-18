---
name: pitch_control_bounds
kind: constant
unit: deg
cluster: perf-oppoints
user_visible: true
source_status: PARTIAL
node_class: unclassified-constant
tags:
  - cluster/perf-oppoints
  - class/unclassified-constant
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Pitch control deflection bounds

**Definition.** Bounds on the pitch-surface deflection variable in the Opti solve.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `±25.0`

**Formula — as the code writes it.**

```
control_variables[pitch_name] = opti.variable(init_guess=0.0, lower_bound=-25.0, upper_bound=25.0)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:619` — `_solve_trim_candidate_with_opti`

**Consumed by.**

- outside it: `app/services/operating_point_generator_service.py:694 (solved_controls)` · `app/services/trim_enrichment_service.py (authority ratio)`

**Source.** 🟡 PARTIAL

> Sadraey §12.1, Table 12.3 — typical elevator maximum deflection: −25° / +20° (asymmetric)
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
delta_E ∈ [−25°, +20°]
```

**⚠️ Divergence from the source.** Magnitude 25° is attributable; the symmetry is not — the source gives an asymmetric range (25° up, 20° down), reflecting the fact that down-elevator stalls the lower tail surface sooner. More importantly the bound is hardcoded and ignores the aircraft's own deflection_limits, which the same context already computed: flaps are clipped to their real TED limit, the elevator is not.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Hard-coded ±25° ignores the aircraft's own deflection_limits, which the code already computed — the flap is clipped to its TED limit but the elevator is not.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
