---
name: mode_default_gamma_climb
symbol: γ
kind: parameter
unit: deg
cluster: perf-matching
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Mode default climb gradient

**Definition.** Per-mode default climb-gradient target.

**Value.** `rc_runway:5.0; rc_hand_launch:5.0; uav_runway:4.0; uav_belly_land:4.0; ga_runway:1.5`

**Formula — as the code writes it.**

```
defaults[mode]["gamma_climb_deg"]
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/matching_chart_service.py:205` — `_mode_defaults`

**Consumed by.**

- in this graph: [[tw_climb_constraint|Climb constraint T/W]]
- outside it: `compute_chart:782` · `_climb_constraint:863` · `hover_text:938`

**Source.** 🔴 NO SOURCE FOUND

> FAR Part 23 §23.65 (via Sadraey §4.3.4, sadraey-rate-of-climb-sizing) requires: reciprocating, MTOW <= 6000 lb, normal/utility/acrobatic -> gradient >= 8.3% landplanes (6.7% seaplanes); reciprocating > 6000 lb and all turbine normal/utility/acrobatic -> >= 4%. No 1.5 deg anywhere.
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**The source states it as.**

```
FAR 23.65: climb gradient >= 8.3% (= 4.74 deg) or >= 4% (= 2.29 deg)
```

**⚠️ Divergence from the source.** MIS-CITATION. The code's ga_runway default gamma = 1.5 deg (approx 2.6%) is attributed to FAR-23.65 but meets NEITHER threshold - it is below the 4% turbine minimum and far below the 8.3% landplane minimum. Either the attribution or the number must change. The RC 5 deg (8.7%) happens to bracket 8.3%, but that is coincidence, not provenance; 5 deg and the UAV 4 deg have no source.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** NO_SOURCE_FOUND for the RC 5° and UAV 4° values; only the GA 1.5° carries a citation.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# γ_climb_min = 1.5° (FAR-23.65 all-engine climb, conservative for GA sizing)`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
