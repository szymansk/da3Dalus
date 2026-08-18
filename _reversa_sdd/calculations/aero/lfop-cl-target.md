---
name: lfop-cl-target
symbol: cl_target
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
  - flag/divergence
---

# Level-flight target lift coefficient

**Definition.** CL required for weight-equals-lift at the assumed cruise speed.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cl_target = (2.0 * mass_kg * g) / (rho * s_ref * cruise_v**2)
```

**Inputs.**

- [[lfop-mass-fallback|Aircraft mass fallback (level-flight solve)]]  — *⤵ fallback*
- [[lfop-g|Gravitational acceleration]]
- [[lfop-rho|Air density (level-flight solve)]]
- [[lfop-s-ref|Reference area (level-flight solve)]]
- [[lfop-cruise-v|Assumed cruise speed (level-flight solve)]]  — *⤵ fallback*

**Produced by.** `app/services/section_aoa_service.py:503` — `_resolve_level_flight_op`

**Consumed by.**

- in this graph: `Target CL clamp`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> Scholz, Flugzeugentwurf, 05_PreliminarySizing §5.6.2, Eq. 5.30 (m_MTO/S_W = C_L * q / g, with q = 0.5*rho*V^2, from L = m*g in steady level flight)
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
C_L = m*g / (q*S) = 2*m*g / (rho * S * V^2)
```

**⚠️ Divergence from the source.** Identical to the cited equation, rearranged for C_L. Load factor is implicitly 1 (steady level flight), which matches the cited derivation.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/section_aoa_service.py:503`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
