---
name: saoa-gamma
symbol: gamma
kind: quantity
unit: m²/s
cluster: aero-strips
user_visible: false
source_status: SOURCED
---

# Panel vortex strength

**Definition.** Bound-vortex circulation of each LiftingLine panel.

**Formula — as the code writes it.**

```
gamma_arr = np.array(ll.vortex_strengths).flatten()
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/section_aoa_service.py:272` — `compute_section_aoa`

**Consumed by.**

- in this graph: [[saoa-cl|Section lift coefficient (Kutta-Joukowski)]]

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
