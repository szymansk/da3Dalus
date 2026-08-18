---
name: mode_default_v_s_target
symbol: V_s_target
kind: parameter
unit: m/s
cluster: perf-matching
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-parameter
tags:
  - cluster/perf-matching
  - class/unclassified-parameter
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Mode default stall-speed target

**Definition.** Per-mode maximum acceptable stall speed driving the stall constraint.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `rc_runway:7.0; rc_hand_launch:7.0; uav_runway:12.0; uav_belly_land:12.0; ga_runway:27.7`

**Formula — as the code writes it.**

```
defaults[mode]["v_s_target"]
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/matching_chart_service.py:205` — `_mode_defaults`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Climb speed for power loading` · `Stall constraint W/S_max`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `compute_chart:781` · `_stall_constraint:868` · `_power_loading_constraint:1133` · `hover_text:952`

**Source.** 🔴 NO SOURCE FOUND

> Regulatory stall limits per Scholz 05_PreliminarySizing §5.1 (landing-field-length-constraint): FAR Part 23 single-engine or multi-engine < 6000 lb -> V_s <= 61 kt (31.4 m/s); EASA CS-VLA -> V_s <= 45 kt (23.2 m/s); FAR Part 25 -> no V_s limit, landing field length binds instead.
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**The source states it as.**

```
FAR-23: V_s <= 61 kt = 31.4 m/s; CS-VLA: V_s <= 45 kt = 23.2 m/s
```

**⚠️ Divergence from the source.** MIS-CITATION. 27.7 m/s = 53.8 kt matches neither limit; it sits between CS-VLA and FAR-23. The comment's '54 kt - FAR-23 max stall speed for Normal/Utility GA' is wrong: the FAR-23 figure is 61 kt. The RC 7 m/s and UAV 12 m/s targets have no source at all.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Even the closest regulatory reference class (CS-VLA, 45 kt) is roughly two orders of magnitude above 0.5-15 kg. The RC/UAV stall targets are mission choices and should carry no regulatory citation.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** NO_SOURCE_FOUND for the 7 m/s RC and 12 m/s UAV targets.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# v_s_target = 27.7 m/s (54 kt — FAR-23 max stall speed for Normal/Utility GA)`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
