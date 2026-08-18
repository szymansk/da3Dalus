---
name: default_altitude_m
kind: constant
unit: m
cluster: perf-oppoints
user_visible: true
source_status: PARTIAL
---

# Default environment altitude

**Definition.** Field altitude used when the aircraft has no flight profile.

**Value.** `0.0`

**Formula — as the code writes it.**

```
"environment": {"altitude_m": 0.0, "wind_mps": 0.0}
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:202` — `_default_profile`

**Consumed by.**

- in this graph: [[aero_coefficients_at_trim|Aero coefficients at the trimmed point]] · [[air_density_rho|Air density at the operating altitude]] · [[op_description_string|Operating-point description]]
- outside it: `app/services/operating_point_generator_service.py:396 (altitude)` · `app/services/operating_point_generator_service.py:661, 769 (asb.Atmosphere)`

**Source.** 🟡 PARTIAL

> Sadraey §4.3.2 / §4.3.5.2: sizing air density is 'always the sea-level value' ρ₀ = 1.225 kg/m³ — worst case for V_s, best case for climb power
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** Sea level as the default reference is the standard sizing convention. That it is also the default *field* altitude for a specific user's aircraft is an app choice, not a source result.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
