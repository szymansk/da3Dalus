---
name: trim-overall-stability-class
symbol: overall_class
kind: quantity
unit: – (enum string)
cluster: stability
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Overall stability class (trim point)

**Definition.** Aggregate stable/neutral/unstable label for a trim point, computed only over the axes whose derivatives are present.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if not known_axes_stable:
    overall = "neutral"  # no data
elif all(known_axes_stable):
    if len(known_axes_stable) == 3:
        overall = "stable"
    else:
        overall = "neutral"  # partially stable but not fully confirmed
else:
    overall = "unstable"  # at least one known axis is unstable
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/trim_enrichment_service.py:157` — `classify_stability`

**Consumed by.**

- outside it: `app/services/trim_enrichment_service.py:172,484` · `app/services/trim_enrichment_service.py:358 (generate_result_summary)` · `frontend/hooks/useOperatingPoints.ts:87`

**Source.** 🟡 PARTIAL

> The three per-axis criteria are individually sourced: C_mα < 0, C_nβ > 0, C_lβ < 0 (Sadraey §11.6.2 Eq. 11.17 and §6.2.2 / §12.6.2). No source prescribes an aggregation rule across the three axes into a single label.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
Longitudinal: C_mα < 0 ; directional: C_nβ > 0 ; lateral: C_lβ < 0
```

**⚠️ Divergence from the source.** Sadraey treats the three axes as INDEPENDENT requirements that must each be satisfied (§6.2.2), not as inputs to a single verdict — and §12.3.3 adds coupled-mode criteria (Dutch roll, spiral, short period) that no per-axis sign test captures. In the code 'neutral' means two different things in one enum ('no data at all' and 'partially confirmed stable'), and it collides semantically with stability_service.classify_stability's 'neutral' = SM in 0–5 %.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** 'neutral' means two different things in the same enum — 'no data at all' and 'partially confirmed stable' — and the user cannot distinguish them. It also collides semantically with stability_service.classify_stability's 'neutral' = SM in 0–5 %.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Missing derivatives are assumed stable (not counted against the
aircraft), but prevent a full "stable" classification`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
