---
name: alr-thickness-match
symbol: —
kind: quantity
unit: dimensionless
cluster: aero-polars
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Mission thickness match multiplier

**Definition.** 1.0 inside the mission thickness band, degrading linearly by 1/5 per percent-chord outside it.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
gap = t_min - max_thickness_pct
thickness_match = max(0.0, 1.0 - gap / 5.0)
```

**Inputs.**

- [[low-re-mission-weights|Mission weighting table]]

**Produced by.** `app/services/airfoil_low_re_service.py:927` — `score_mission`

**Consumed by.**

- in this graph: `Mission suitability score`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `score_mission:939`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source for the 5 %-chord linear decay width. Additionally the defaults t_min=0.0 / t_max=100.0 (lines 913-914) make the multiplier identically 1.0 for any mission whose weight dict omits the band — inert rather than neutral by design.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The 5.0 percent-chord decay width is a magic number and the band defaults (t_min=0.0, t_max=100.0, lines 913-914) make the multiplier inert for any mission whose weight dict omits them.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `gap = t_min - max_thickness_pct
thickness_match = max(0.0, 1.0 - gap / 5.0)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
