---
name: ws_sweep_steps
symbol: n_WS
kind: constant
unit: count
cluster: perf-matching
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/perf-matching
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
---

# W/S sweep resolution

**Definition.** Number of sample points along the W/S axis.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `200`

**Formula — as the code writes it.**

```
_WS_STEPS: int = 200
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/matching_chart_service.py:73` — `_WS_STEPS`

**Consumed by.**

- in this graph: `W/S sweep vector`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `ws_range:838`

**Source.** 🔴 NO SOURCE FOUND

> Numerical resolution choice; no source. The sources construct the chart graphically (Sadraey §4.3.1 steps 1-2) and do not prescribe a sample count.
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**Cited in the code itself.** `# number of points in W/S sweep`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
