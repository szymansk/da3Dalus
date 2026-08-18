---
name: saoa-cl
symbol: cl
kind: quantity
unit: dimensionless
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

# Section lift coefficient (Kutta-Joukowski)

**Definition.** Section cl from circulation via the 2D Kutta-Joukowski relation.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cl_arr = 2.0 * gamma_arr / (vmag * chord_arr)
```

**Inputs.**

- [[saoa-gamma|Panel vortex strength]]  — *⊣ limit*
- [[saoa-vmag|Local velocity magnitude]]
- [[saoa-chord|Panel chord]]

**Produced by.** `app/services/section_aoa_service.py:279` — `compute_section_aoa`

**Consumed by.**

- in this graph: `Effective angle of attack` · `Section cd at a target CL and trip position` · `Area-weighted mean section CL` · `Representative lift coefficient (whole scope)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/api/v2/endpoints/section_aoa.py:SectionAoaPoint.cl` · `app/services/turbulator_optimizer_service.py:build_wing_section_data` · `frontend/hooks/useSectionAoa.ts`

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §3.16 (Kutta-Joukowski, L' = rho_inf * V_inf * Gamma) and §5.3 (c_l = 2*Gamma / (V_inf * c))
>
> — via `aerodynamics-expert`

**The source states it as.**

```
c_l = 2 * Gamma / (V_inf * c)
```

**⚠️ Divergence from the source.** The textbook relation uses the FREESTREAM velocity; the code divides by the LOCAL velocity magnitude at the vortex centre. Both are defensible — the resultant force perpendicular to the local wind has magnitude rho*V_eff*Gamma, so the local form yields the effective (section-frame) cl, which is in fact the quantity you must have to invert through the section lift curve into alpha_eff. It is self-consistent with saoa-alpha-eff but it is NOT Anderson's expression, and it is a different cl from the one vlm_strip_forces publishes under the same name.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Two producers of section cl(y): this LiftingLine value (8 panels/half) and vlm_strip_forces' strip cl (40 panels/half) — different methods, both user-visible (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/section_aoa_service.py:279`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
