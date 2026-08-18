---
name: sui-tip-re-flag
symbol: —
kind: quantity
unit: boolean
cluster: aero-polars
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# tip_re_flag

**Definition.** True when the tip Reynolds is below an absolute floor or drops far below the root Re.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
tip_re_flag_all = (
    re_tip < settings.low_re_tip_re_abs_floor
    or (re_root - re_tip) > settings.low_re_tip_re_rel_drop
)
```

**Inputs.**

- [[sui-re-root|Root-chord Reynolds number]]
- [[low-re-tip-re-abs-floor|Tip-Re absolute floor]]  — *⊣ limit*
- [[low-re-tip-re-rel-drop|Tip-Re relative drop threshold]]  — *⊣ limit*

**Produced by.** `app/services/suitability_service.py:273` — `search_suitability`

**Consumed by.**

- outside it: `SuitabilityItem.tip_re_flag:568` · `frontend AirfoilSuitabilityCard.tsx:351`

**Source.** 🟡 PARTIAL

> RC-Network Wiki 'Re-Zahl' — model aircraft operate near Re_crit, so lift and drag coefficients change strongly with small Re changes; a tapered wing's tip can therefore sit in a different regime from the root
>
> — via `rc-aircraft-designer, aerodynamics-expert`

**⚠️ Divergence from the source.** The physical concern is sourced. The OR-combination of an absolute floor and an absolute difference is not, and neither threshold is cited. Structural problem: computed once per query yet copied onto every item, while AirfoilSuitabilityCard.tsx:349-351 documents it as per-airfoil.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Computed once per query and copied onto every item, yet AirfoilSuitabilityCard.tsx:349-351 comments that 'Only the per-airfoil item.tip_re_flag indicates that this specific' airfoil is affected — the UI treats a query-global flag as per-airfoil.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `tip_re_flag_all = (
    re_tip < settings.low_re_tip_re_abs_floor
    or (re_root - re_tip) > settings.low_re_tip_re_rel_drop
)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
