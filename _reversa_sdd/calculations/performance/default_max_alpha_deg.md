---
name: default_max_alpha_deg
symbol: α_max
kind: constant
unit: deg
cluster: perf-oppoints
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Default maximum angle of attack

**Definition.** Alpha limit used for the Opti upper bound and the ALPHA_LIMIT_REACHED check.

**Value.** `25.0`

**Formula — as the code writes it.**

```
"constraints": {"max_alpha_deg": 25.0, "max_beta_deg": 30.0}
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:212` — `_default_profile`

**Consumed by.**

- in this graph: [[alpha_bounds_opti|Opti alpha bounds and initial guess]] · [[warn_alpha_limit_reached|ALPHA_LIMIT_REACHED warning]]
- outside it: `app/services/operating_point_generator_service.py:596 (Opti upper bound)` · `app/services/operating_point_generator_service.py:859-862 (ALPHA_LIMIT_REACHED)`

**Source.** 🔴 NO SOURCE FOUND

> Contradicted by: Sadraey §5.4.3 / Scholz 08_HighLift §8.2 — 'Stall angle α_s — typically 12–16°'; Anderson, Fundamentals of Aerodynamics 6e §4.3/§4.13 — NACA 2412 stalls at ≈16°, massive separation above 15°
>
> — via `aircraft-design-scholz, aerodynamics-expert`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 25° is roughly 10° above the physical stall angle of any conventional section, so the ALPHA_LIMIT_REACHED check can essentially never fire on a default profile, and it also sets the Opti upper bound — the solver is free to search deep into post-stall alpha where AeroBuildup's polar is least trustworthy. The app's own schema (flight_profile.py:221) says 'typical values are 10 to 16 deg', matching the sources; the default contradicts the schema's own documentation.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** 25° is far above the physical stall alpha of an RC/UAV wing; app/schemas/flight_profile.py:221 itself says "Typical values are 10 to 16 deg", so the default never triggers the limit.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
