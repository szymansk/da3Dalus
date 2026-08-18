---
name: roll_control_bounds
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

# Roll control deflection bounds

**Definition.** Bounds on the roll-surface deflection variable in turn solves.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `±20.0`

**Formula — as the code writes it.**

```
control_variables[roll_name] = opti.variable(init_guess=0.0, lower_bound=-20.0, upper_bound=20.0)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:623` — `_solve_trim_candidate_with_opti`

**Consumed by.**

- outside it: `app/services/operating_point_generator_service.py:694`

**Source.** 🟡 PARTIAL

> Sadraey §12.1, Table 12.3 — aileron ±25°; §12.4.4 design procedure step 10: 'Select maximum deflection δ_Amax (typically ±25°)'; Sadraey's own aileron design example (§12.4) uses δ_Amax = ±20°
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
delta_A,max typically ±25°, worked examples ±20°
```

**⚠️ Divergence from the source.** ±20° matches one worked example but not the source's stated typical value (±25°) — and it is 5° tighter than the pitch and yaw bounds in the same function with no reason given. Also hardcoded rather than read from the surface's TED limits.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** ±20° differs from the pitch/yaw ±25° with no stated reason and again ignores the surface's TED limit.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
