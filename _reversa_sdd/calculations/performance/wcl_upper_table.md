---
name: wcl_upper_table
symbol: WCL_max
kind: constant
unit: lb/ft^4.5
cluster: perf-matching
user_visible: true
source_status: PARTIAL
node_class: unclassified-constant
tags:
  - cluster/perf-matching
  - class/unclassified-constant
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Lennon WCL upper bounds

**Definition.** Per-profile wing-cube-loading ceilings in Lennon's imperial units.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `trainer:6.0; sport:12.0`

**Formula — as the code writes it.**

```
_WCL_UPPER_BY_PROFILE_LB_FT45: dict[str, float] = {"trainer": 6.0, "sport": 12.0}
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/matching_chart_service.py:456` — `_WCL_UPPER_BY_PROFILE_LB_FT45`

**Consumed by.**

- in this graph: `WCL-derived W/S ceiling`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_wcl_constraint:517`

**Source.** 🟡 PARTIAL

> Not in Scholz or Sadraey - wing cube loading is an RC-community metric with no academic counterpart. In-code attribution to Lennon, 'Basics of R/C Model Aircraft Design', unverified.
>
> — via `aircraft-design-scholz (no coverage)`

**The source states it as.**

```
WCL = weight / (wing area)^1.5
```

**⚠️ Divergence from the source.** The VALUES 6 (trainer) and 12 (sport) are the standard RC wing-cube-loading bands expressed in oz/ft^3, the conventional unit for this metric - not 'lb/ft^4.5' as the code labels them. The unit label is wrong, and the conversion built on that label (see lennon_lb_ft_to_si) is therefore wrong too. A commented-out glider value of 4.0 is left as dead documentation (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** A commented-out glider value of 4.0 is left in the source as dead documentation (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# WCL upper bound per profile (Lennon's mission-consistent ranges, lb/ft^4.5). Lennon convention; converted to SI below. Racer / glider unconstrained here.`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
