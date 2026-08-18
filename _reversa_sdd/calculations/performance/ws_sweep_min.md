---
name: ws_sweep_min
symbol: W/S_min
kind: constant
unit: N/m^2
cluster: perf-matching
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/perf-matching
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - flag/divergence
---

# W/S sweep lower bound

**Definition.** Lower bound of the wing-loading axis of the matching chart.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `10.0`

**Formula — as the code writes it.**

```
_WS_MIN: float = 10.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/matching_chart_service.py:71` — `_WS_MIN`

**Consumed by.**

- in this graph: `W/S sweep vector`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `ws_range:838`

**Source.** 🔴 NO SOURCE FOUND

> Sadraey 2013 §4.3.1 step 2 gives explicit guidance - suggested W/S range 5-100 lb/ft^2 (approx 240-4790 N/m^2) - and warns 'do NOT start at zero (W/P contains 1/(W/S) terms that diverge)'. 10 N/m^2 is not in that guidance.
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**The source states it as.**

```
Sadraey step 2: sweep W/S over 5-100 lb/ft^2, never from zero
```

**⚠️ Divergence from the source.** 10 N/m^2 (about 1 kg/m^2) is below any flyable aircraft and is effectively the 'near zero' Sadraey warns against: the parasite term q*CD0/(W/S) in the cruise constraint diverges there, wasting chart range on an unphysical region.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `# N/m² — lower bound for W/S sweep`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
