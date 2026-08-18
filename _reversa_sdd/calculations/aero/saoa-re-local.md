---
name: saoa-re-local
symbol: re_local
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: false
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
---

# Local chord Reynolds number (alpha_L0 lookup)

**Definition.** Chord Reynolds number at a cross-section, floored to avoid Re=0.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
re_local = max(velocity * chord / nu, 1e4)  # avoid Re=0
```

**Inputs.**

- [[saoa-velocity-fallback|Velocity fallback for Reynolds]]  — *⤵ fallback*
- [[saoa-chord-fallback|Chord fallback for Reynolds]]  — *⤵ fallback*
- [[saoa-nu|Kinematic viscosity (section AoA)]]

**Produced by.** `app/services/section_aoa_service.py:162` — `_compute_alpha_l0_per_section`

**Consumed by.**

- in this graph: `Section zero-lift angle`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §1.7 and §4.12 (Re_c = rho_inf * V_inf * c / mu_inf)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
Re_c = V * c / nu
```

**Cited in the code itself.** `app/services/section_aoa_service.py:162`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
