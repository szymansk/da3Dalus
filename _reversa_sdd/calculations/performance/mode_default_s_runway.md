---
name: mode_default_s_runway
symbol: s_runway
kind: parameter
unit: m
cluster: perf-matching
user_visible: true
source_status: PARTIAL
---

# Mode default field length

**Definition.** Per-mode default field-length target used when the caller supplies no override.

**Value.** `rc_runway:50.0; rc_hand_launch:0.0; uav_runway:200.0; uav_belly_land:200.0; ga_runway:500.0`

**Formula — as the code writes it.**

```
defaults[mode]["s_runway"]
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/matching_chart_service.py:205` — `_mode_defaults`

**Consumed by.**

- in this graph: [[tw_takeoff_constraint|Takeoff constraint T/W]] · [[ws_landing_constraint|Landing constraint W/S_max]]
- outside it: `compute_chart:780` · `_takeoff_constraint:843` · `_landing_constraint:850` · `hover_text:896,910`

**Source.** 🟡 PARTIAL

> Only the GA value has a defensible anchor: 500 m is a plausible paved GA field length to 50 ft (FAR-23 §23.53 obstacle, Scholz 05_PreliminarySizing §5.2). The RC (50 m), hand-launch (0 m) and UAV (200 m) values have no source in Scholz or Sadraey.
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** An unknown mode silently returns the uav_runway defaults with only a logger.warning and no DesignWarning to the caller (ADR 0020). Also: s_runway <= 0 makes the takeoff constraint return exactly 0.0, an undeclared 'constraint disabled' path.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** The one sourced value in the table is the GA one; the RC/UAV values that actually matter for the target class are unsourced mission choices and should be labelled as such rather than sitting alongside a cited number.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** An unknown mode silently returns the uav_runway defaults with only a logger.warning and no DesignWarning to the caller (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# s_runway = 500 m (typical paved GA airfield field length to 50 ft)`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
