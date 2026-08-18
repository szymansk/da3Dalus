---
name: mu_brake_hard
symbol: μ_brake
kind: constant
unit: dimensionless
cluster: perf-matching
user_visible: false
source_status: PARTIAL
---

# Braking friction, hard runway

**Definition.** Wheel-braking friction coefficient on a dry hard runway.

**Value.** `0.4`

**Formula — as the code writes it.**

```
_MU_BRAKE_HARD: float = 0.4
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/field_length_service.py:88` — `_MU_BRAKE_HARD`

**Consumed by.**

- in this graph: [[k_ldg_adjusted|Friction-adjusted landing coefficient]] · [[mu_brake_selected|Selected braking friction]]
- outside it: `_compute_s_ldg_ground default:239` · `_compute_s_ldg_ground:263 (numerator of ratio)` · `compute_field_lengths:433`

**Source.** 🟡 PARTIAL

> The only friction table in the lead authority is Sadraey 2013 Table 4.15, and it is ROLLING friction for the takeoff ground roll (dry concrete/asphalt 0.03-0.05, wet 0.05, icy 0.02, turf 0.04-0.07, grass 0.05-0.1, soft ground 0.1-0.3). Braking friction is not tabulated; Scholz treats deceleration as a lumped a_braking (exam-matching-chart-design-point).
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** 0.4 is roughly an order of magnitude above Sadraey's rolling values, which is physically correct (brakes vs free-rolling) but means the code is using a quantity the lead authority never gives. The general concept is standard; this specific value is not attributable to Scholz or Sadraey.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `# braking, dry hard runway`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
