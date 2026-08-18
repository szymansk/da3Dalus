---
name: k_ldg_50ft
symbol: k_LDG_50ft
kind: constant
unit: dimensionless
cluster: perf-matching
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Landing 50-ft obstacle factor

**Definition.** Multiplier converting landing ground roll to total distance from a 50-ft obstacle.

**Value.** `2.73`

**Formula — as the code writes it.**

```
_K_LDG_50FT: float = (2.73)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/field_length_service.py:76` — `_K_LDG_50FT`

**Consumed by.**

- in this graph: [[s_ldg_50ft|Landing distance from 50 ft]] · [[s_obstacle_factor_apply|Obstacle-corrected distance]] · [[ws_landing_constraint|Landing constraint W/S_max]]
- outside it: `compute_field_lengths:436` · `matching_chart_service._landing_constraint:341` · `matching_chart hover_text:910`

**Source.** 🔴 NO SOURCE FOUND

> Nothing in Scholz 05_PreliminarySizing §5.1 or Sadraey §4.3.2 supports 2.73. The nearest sourced multipliers are regulatory DISPATCH margins, a different quantity: CS-OPS 1.515 s_LFL = s_L/0.6 = 1.667*s_L (turbojet), s_L/0.7 = 1.429*s_L (turboprop) - applied to an already-complete 50-ft distance, not to a ground roll.
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** The code's own comment admits the value is a back-calculation from a Cessna 172N POH (410 m / 150 m), i.e. a one-point curve fit presented as a constant.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Calibrated on a 1088 kg GA aircraft and applied to 0.5-15 kg. The air-phase fraction of the 50-ft distance scales with approach speed and flight-path angle; a 2 kg model at ~12 m/s has a completely different air/ground split than a 172 at ~30 m/s. Direct ADR 0023 violation.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Calibrated against a Cessna 172N POH (1088 kg) and then used for the 0.5–15 kg target class — a transport/GA-category calibration, an ADR 0023 finding.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"Roskam gives k_LDG_50ft ≈ 1.5 for the *air phase alone*; the full total-from-50ft multiplier (air + ground) is ~2.5–3.0. The Cessna 172N POH cross-check calibrates this to 2.73 (410 m / 150 m)."`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
