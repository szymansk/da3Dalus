---
name: deflection-usage-fraction
symbol: —
kind: quantity
unit: – (fraction)
cluster: stability
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Deflection usage fraction

**Definition.** Fraction of the available mechanical deflection consumed at this trim point.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
usage = abs(deflection_deg) / limit if limit > 0 else 0.0
```

**Inputs.**

- [[deflection-limit-default|Default control-surface deflection limit]]  — *⤵ fallback*

**Produced by.** `app/services/trim_enrichment_service.py:415` — `compute_enrichment`

**Consumed by.**

- in this graph: `Elevator reserve percentage (summary text)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/trim_enrichment_service.py:420,426,438,348` · `frontend/components/workbench/trim-interpretation/ControlAuthorityChart.tsx` · `frontend/components/workbench/trim-interpretation/OpComparisonTable.tsx`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §12.5.5 steps 18–19 — plot required δ_E versus airspeed (the trim curve) and compare the maximum required deflection against the design deflection limit; if it exceeds the limit, the surface must be enlarged. Expressing that comparison as a fraction of available travel is the direct numerical form of step 19.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
Compare max required δ_E against δ_E,max from step 4; exceeding it means 'no elevator can satisfy trim' → redesign (Sadraey §12.5.5 step 19)
```

**⚠️ Divergence from the source.** Sadraey's comparison is against the SPECIFIC surface's design limit. Here the denominator is the 25° fallback in every observed case (see deflection-limit-default), so the number the UI labels 'authority used' is scaled by 25° regardless of the real hinge limits. Sadraey's response to exceeding the limit is also categorical (redesign, return to step 5), not a graded percentage.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Computed against the wrong denominator in every observed case (see deflection-limit-default) — the number the UI shows as 'authority used' is scaled by 25° regardless of the real hinge limits.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
