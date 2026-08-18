---
name: gravity_g
symbol: g
kind: constant
unit: m/s²
cluster: perf-oppoints
user_visible: false
source_status: SOURCED
---

# Gravitational acceleration

**Definition.** Standard gravity used to convert mass into required lift.

**Value.** `9.81`

**Formula — as the code writes it.**

```
(total_mass_kg * 9.81 * n_target) / (q_dyn * s_ref)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:797` — `_cl_target_for_velocity`

**Consumed by.**

- in this graph: [[cl_target|Target lift coefficient]]
- outside it: `app/services/operating_point_generator_service.py:797`

**Source.** 🟢 SOURCED

> Standard gravity g_n = 9.80665 m/s² (CGPM 1901; ISO 80000-3; basis of the ICAO/ISA standard atmosphere). Scholz and Sadraey both use g = 9.81 m/s² throughout their worked examples (e.g. Scholz 05_PreliminarySizing example-wing-loading-landing; Sadraey §10.4 weight examples).
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
g = 9.80665 m/s² exact; 9.81 as the engineering rounding used by both authorities
```

**⚠️ Divergence from the source.** 9.81 vs 9.80665 is a 0.034 % error — physically irrelevant at RC/UAV scale and consistent with both cited textbooks. The real finding is duplication: turn_kinematics.py:14 defines its own _G = 9.81 rather than sharing one constant (two producers of one physical constant).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Second producer of g: app/services/turn_kinematics.py:14 defines its own module constant _G = 9.81 rather than sharing one.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
