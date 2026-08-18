---
name: ga_runway_mode
symbol: ga_runway
kind: parameter
unit: n/a
cluster: perf-matching
user_visible: false
source_status: PARTIAL
node_class: unclassified-parameter
tags:
  - cluster/perf-matching
  - class/unclassified-parameter
  - source/partial
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# GA runway mode

**Definition.** FAR-23.65 Cessna-172-class default set inside _mode_defaults.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `s_runway=500.0, gamma_climb_deg=1.5, v_s_target=27.7`

**Formula — as the code writes it.**

```
"ga_runway": {"s_runway": 500.0, "gamma_climb_deg": 1.5, "v_s_target": 27.7}
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/matching_chart_service.py:233` — `_mode_defaults`

**Consumed by.**

- outside it: `app/tests/test_matching_chart.py:874 ONLY`

**Source.** 🟡 PARTIAL

> Mixed. The uncited comment values are the defensible ones: mu_friction ~0.04 sits inside Sadraey Table 4.15 dry concrete/asphalt ROLLING friction 0.03-0.05, and CL_max_takeoff ~1.6 sits inside Scholz Table 5.1 single-engine propeller CL_max,TO 1.3-1.9. The values the code actually uses are not: gamma 1.5 deg mis-cites FAR-23.65 (>= 8.3% or 4%), and v_s 27.7 m/s mis-cites FAR-23 (61 kt = 31.4 m/s).
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** The block documents two sourceable constants (mu = 0.04, CL_max_TO = 1.6) that no code reads, while the three constants that are read are the mis-cited ones. Also unreachable from the API - schemas/matching_chart.py:9 omits 'ga_runway' from the AircraftMode Literal, so only tests can select it (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** The whole block is manned GA (Cessna 172-class) and by construction irrelevant to 0.5-15 kg.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Unreachable from the API — schemas/matching_chart.py:9 AircraftMode Literal omits 'ga_runway', so only tests can select it (ADR 0021 inert code); the block also documents μ=0.04 and CL_max_TO=1.6 that no code reads.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# FAR-23.65 single-engine GA (Cessna 172-class): μ_friction ≈ 0.04 (hard paved runway, ICAO Annex 14); CL_max_takeoff ≈ 1.6 (typical GA flaps-10 setting)`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
