---
name: v_best_angle_climb_vx
symbol: Vx
kind: quantity
unit: m/s
cluster: perf-oppoints
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-oppoints
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Vx target speed

**Definition.** Speed assigned to the best-angle-of-climb operating point.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
"velocity": max(1.35 * refs["vs_clean"], cruise * 0.85)
```

**Inputs.**

- [[vs_clean|Clean stall speed reference]]
- [[cruise_speed_resolved|Resolved cruise speed]]

**Produced by.** `app/services/operating_point_generator_service.py:426` — `_build_target_definitions`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/models/analysismodels.py (velocity)` · `app/services/flight_envelope_service.py:601`

**Source.** 🔴 NO SOURCE FOUND

> Defining authority: Sadraey §4.3.5 — climb angle follows from T − D (Eq. 4.78, ROC = V(T/W − 1/(L/D))); V_x is the speed maximising excess *thrust*, not a fixed multiple of V_s. No k·V_s rule of thumb for V_x exists in Sadraey, Scholz, Anderson or Lennon.
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**The source states it as.**

```
sin(gamma) = T/W − 1/(L/D); V_x maximises (T − D)
```

**⚠️ Divergence from the source.** max(1.35·V_s, 0.85·cruise) is not derived from any climb quantity — no thrust, no drag polar, no L/D. The operating point is *labelled* best-angle-of-climb but is a fixed fraction of speeds unrelated to climb. The name asserts a physical optimum the calculation never computes. Both multipliers are unsourced.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Vx is named for the speed maximising climb angle but is set by two ad-hoc multipliers (1.35, 0.85) rather than by any climb-performance calculation — the name contradicts the definition.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
