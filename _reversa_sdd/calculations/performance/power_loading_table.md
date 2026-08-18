---
name: power_loading_table
symbol: P/m
kind: constant
unit: W/kg
cluster: perf-matching
user_visible: true
source_status: PARTIAL
---

# Power-loading bands

**Definition.** Per-profile lower-bound specific power used to derive a T/W floor.

**Value.** `trainer:125.0; sport:200.0; wing_racer:275.0; acro_3d:400.0`

**Formula — as the code writes it.**

```
_POWER_LOADING_W_PER_KG: dict[str, float] = {"trainer": 125.0, "sport": 200.0, "wing_racer": 275.0, "acro_3d": 400.0}
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/matching_chart_service.py:466` — `_POWER_LOADING_W_PER_KG`

**Consumed by.**

- in this graph: [[tw_power_loading|Power-loading T/W floor]]
- outside it: `_power_loading_constraint:560`

**Source.** 🟡 PARTIAL

> Nothing in Scholz or Sadraey - specific power by RC mission class has no academic counterpart. In-code attribution to Lennon Ch. 9, unverified. The values do map onto the well-known RC watts-per-pound bands (roughly 55/90/125/180 W/lb for trainer/sport/racer/3D), which supports plausibility but is not a citation.
>
> — via `aircraft-design-scholz (no coverage; in-code Lennon Ch.9 claim unverified)`

**⚠️ Divergence from the source.** The comment states the values are converted to a T/W floor via T = P*eta_prop/V_climb with V_climb = 1.3*V_stall; that conversion chain is where the unsourced content actually lives (see v_climb_power_loading).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** RC-native metric; no transport-category cross-check exists, so it cannot be validated against the lead authority.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**Cited in the code itself.** `# Source: Lennon Ch. 9 "power-to-weight" ranges. Numbers are P/m (W/kg), converted to a T/W floor via T = P · η_prop / V_climb, V_climb = 1.3 V_stall.  (trainer: 100–150 W/kg, mid; sport: 150–250 W/kg, mid; wing_racer: 250+ W/kg; acro_3d: 400+ W/kg, unlimited 3D)`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
