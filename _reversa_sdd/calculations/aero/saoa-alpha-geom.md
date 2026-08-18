---
name: saoa-alpha-geom
symbol: alpha_geometric_deg
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

# Geometric angle of attack

**Definition.** Trim alpha plus the local geometric twist at each panel.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
alpha_geom_arr = op_alpha_deg + twist_at_y  # [deg]
```

**Inputs.**

- [[saoa-twist-at-y|Interpolated twist at panel y]]

**Produced by.** `app/services/section_aoa_service.py:326` — `compute_section_aoa`

**Consumed by.**

- in this graph: `Induced downwash angle`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/api/v2/endpoints/section_aoa.py:SectionAoaPoint.alpha_geometric_deg` · `frontend/hooks/useSectionAoa.ts`

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §5.1 and §5.3 (geometric angle of attack at a spanwise station, measured from the freestream, including local incidence/twist)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
alpha_geometric(y) = alpha_freestream + i_local(y)
```

**⚠️ Divergence from the source.** The formula is right IF xsec.twist is the absolute incidence of the section relative to the body x-axis. The module docstring (line 26) and the endpoint description both claim alpha_geom = op_alpha + incidence_w + twist(y), i.e. that twist is relative to a separate wing incidence — which the code does not add. Documentation and code state two different models; only one can be correct and nothing in the code decides which.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Module docstring (line 26) and endpoint description both state alpha_geom = op_alpha + incidence_w + twist(y), but the code adds only twist_at_y — the name/definition and the formula disagree unless xsec.twist is taken as absolute.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/section_aoa_service.py:313,326`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
