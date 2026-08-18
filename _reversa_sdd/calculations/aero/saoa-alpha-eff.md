---
name: saoa-alpha-eff
symbol: alpha_effective_deg
kind: quantity
unit: deg
cluster: aero-strips
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Effective angle of attack

**Definition.** Section AoA implied by cl through the thin-airfoil lift curve, offset by the zero-lift angle.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
alpha_eff_arr = np.degrees(cl_arr / _A0_RAD) + alpha_L0_at_y
```

**Inputs.**

- [[saoa-cl|Section lift coefficient (Kutta-Joukowski)]]
- [[saoa-a0|Thin-airfoil lift-curve slope]]
- [[saoa-alpha-l0-at-y|Interpolated zero-lift angle at panel y]]

**Produced by.** `app/services/section_aoa_service.py:300` — `compute_section_aoa`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Induced downwash angle`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/api/v2/endpoints/section_aoa.py:SectionAoaPoint.alpha_effective_deg` · `frontend/app/workbench/airfoil-preview/page.tsx:297`

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §5.3 (the LLT section closure: c_l = 2*pi*(alpha_eff - alpha_L=0))
>
> — via `aerodynamics-expert`

**The source states it as.**

```
alpha_eff = c_l / (2*pi) + alpha_L=0  (alpha in radians)
```

**⚠️ Divergence from the source.** Exact algebraic inversion of the cited closure. Its accuracy is bounded entirely by the a_0 = 2*pi assumption (see saoa-a0) and by the alpha_L0 fallbacks.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/section_aoa_service.py:300`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
