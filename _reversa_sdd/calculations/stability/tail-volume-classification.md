---
name: tail-volume-classification
symbol: —
kind: quantity
unit: – (enum string)
cluster: stability
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Tail volume classification

**Definition.** Bands a volume coefficient into out_of_physical_range / below_range / above_range / in_range.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if value < phys_min or value > phys_max:
    return "out_of_physical_range"
if value < target_min:
    return "below_range"
if value > target_max:
    return "above_range"
return "in_range"
```

**Inputs.**

- [[v-h-current|Horizontal tail volume coefficient]]
- [[v-v-current|Vertical tail volume coefficient]]
- [[v-h-physical-min|V_H physical minimum]]  — *⊣ limit*
- [[v-h-physical-max|V_H physical maximum]]  — *⊣ limit*
- [[v-v-physical-min|V_V physical minimum]]  — *⊣ limit*
- [[v-v-physical-max|V_V physical maximum]]  — *⊣ limit*
- [[aircraft-class-tail-targets|Tail-volume target ranges by aircraft class]]

**Produced by.** `app/services/tail_sizing_service.py:316` — `_classify_volume`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/tail_sizing_service.py:247,253,266,270,275,282,286,291,298` · `app/api/v2/endpoints/aeroplane/tail_sizing.py:87-89` · `frontend/components/workbench/TailVolumeCard.tsx`

**Source.** 🟡 PARTIAL

> Comparing V_H/V_V against per-type reference bands is exactly the preliminary-sizing method of Sadraey §6.7.1 (Tables 6.4/6.5) and rcplanedesigner.com's mission-consistent ranges. The specific four-label banding (out_of_physical_range / below_range / above_range / in_range) is a code construct with no source.
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
Compare V̄_H against the type band (Sadraey Table 6.4) and V̄_V against Table 6.5
```

**⚠️ Divergence from the source.** Both sources present the bands as starting points for a design that is then verified by trim and stability calculation — Sadraey §6.7.1 solves Eq. 6.29 for C_Lh and iterates; rcplanedesigner states the ranges "do not replace balance checks, airfoil choice, elevator sizing, or flight testing." The code's terminal labels, especially 'out_of_physical_range', assert more than either source supports (see v-h-physical-min).

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
