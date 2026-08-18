---
name: saoa-gamma
symbol: gamma
kind: quantity
unit: m²/s
cluster: aero-strips
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
  - audit/confirmed
  - solver-adjacent/liftingline
---

# Panel vortex strength

**Definition.** Bound-vortex circulation of each LiftingLine panel.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
gamma_arr = np.array(ll.vortex_strengths).flatten()
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/section_aoa_service.py:272` — `compute_section_aoa`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Section lift coefficient (Kutta-Joukowski)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §5.3 (Prandtl lifting line: bound circulation distribution Gamma(y))
>
> — via `aerodynamics-expert`

**The source states it as.**

```
Gamma(y) = bound vortex strength at spanwise station y
```

**Cited in the code itself.** `app/services/section_aoa_service.py:272`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
