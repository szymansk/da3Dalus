---
name: yaw_control_bounds
kind: constant
unit: deg
cluster: perf-oppoints
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/perf-oppoints
  - class/unclassified-constant
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Yaw control deflection bounds

**Definition.** Bounds on the yaw-surface deflection variable in turn / dutch-roll solves.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `±25.0`

**Formula — as the code writes it.**

```
control_variables[yaw_name] = opti.variable(init_guess=0.0, lower_bound=-25.0, upper_bound=25.0)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:629` — `_solve_trim_candidate_with_opti`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/operating_point_generator_service.py:694`

**Source.** 🟡 PARTIAL

> Sadraey §12.1, Table 12.3 — rudder ±30°; §12.6.1: 'δ_Rmax = ±30°', with the Cessna 182 listed at ±24° and a light-GA design example at ±25°
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
delta_R,max typically ±30° (light GA ±24…25°)
```

**⚠️ Divergence from the source.** ±25° is inside the range spanned by the source's light-aircraft examples but below its stated typical ±30°. For a 0.5–15 kg aircraft the light-GA end is the more relevant anchor, so the value is defensible — but it is unstated and again ignores the surface's own limits.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
