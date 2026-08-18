---
name: saoa-induced-angle
symbol: induced_angle_deg
kind: quantity
unit: deg
cluster: aero-strips
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Induced downwash angle

**Definition.** Geometric minus effective angle of attack at each panel.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
induced_angle_arr = alpha_geom_arr - alpha_eff_arr
```

**Inputs.**

- [[saoa-alpha-geom|Geometric angle of attack]]
- [[saoa-alpha-eff|Effective angle of attack]]

**Produced by.** `app/services/section_aoa_service.py:337` — `compute_section_aoa`

**Consumed by.**

- outside it: `app/api/v2/endpoints/section_aoa.py:SectionAoaPoint.induced_angle_deg` · `frontend/hooks/useSectionAoa.ts`

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §5.1 (alpha_eff = alpha - alpha_i)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
alpha_i = alpha - alpha_eff
```

**⚠️ Divergence from the source.** Exact rearrangement of the cited relation. Refusing to clamp negatives is correct — upwash (negative alpha_i) is physically real inboard of a strongly loaded tip. The problem is duplication: vlm_strip_forces publishes an 'ai' from a force ratio at 40 panels/half while this publishes an 'induced_angle_deg' from geometry minus a 2*pi inversion at 8 panels/half.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Second producer of the induced angle alongside vlm_strip_forces' ai (ADR 0022); the code comment explicitly forbids clamping negative values.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/section_aoa_service.py:337`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
