---
name: mkpi_normalise_score
symbol: score_0_1
kind: quantity
unit: -
cluster: perf-envelope
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Axis normalisation

**Definition.** Linear mapping of a physical value onto the mission preset's axis range, clipped to [0,1].

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if hi <= lo: return 0.0; score = (value - lo) / (hi - lo); return max(0.0, min(1.0, score))
```

**Inputs.**

- [[mkpi_axis_ranges|Mission axis ranges]]  — *⊣ limit*

**Produced by.** `app/services/mission_kpi_service.py:65` — `_normalise_score`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Soll polygon scores`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `MissionRadarChart.tsx` · `AxisDrawer.tsx`

**Source.** 🟢 SOURCED

> Linear min-max normalisation — a presentation transform, no engineering source applies.
>
> — via `scholz`

**The source states it as.**

```
score = clip((value - lo)/(hi - lo), 0, 1)
```

**⚠️ Divergence from the source.** ADR 0020 clamp: an aircraft far outside the mission band scores exactly 1.0 (or 0.0) with provenance 'computed' and no warning, so the radar cannot distinguish 'meets target' from 'wildly exceeds target'. For a design tool that is a meaningful loss — exceeding a mission band by 3x is usually a design signal, not a success.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Clipping is silent: an aircraft far outside the mission band scores exactly 1.0 (or 0.0) with provenance 'computed' and no warning, so the radar cannot distinguish 'meets target' from 'wildly exceeds target' (ADR 0020 clamp).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
