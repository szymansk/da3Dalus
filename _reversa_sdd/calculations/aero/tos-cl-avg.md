---
name: tos-cl-avg
symbol: cl_avg
kind: quantity
unit: dimensionless
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
  - flag/divergence
---

# Area-weighted mean section CL

**Definition.** Wing-average lift coefficient used as the numerator of the L/D summary.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cl_avg = sum(s.cl * s.section_area_m2 for s in sections) / total_area if total_area > 0 else sections[0].cl
```

**Inputs.**

- [[saoa-cl|Section lift coefficient (Kutta-Joukowski)]]
- [[bwsd-section-area-normalised|Normalised section area]]

**Produced by.** `app/services/turbulator_optimizer_service.py:607` — `run_turbulator_optimizer`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Clean lift-to-drag ratio` · `Tripped lift-to-drag ratio`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §5.3 (C_L = (2/(V_inf*S)) integral Gamma(y) dy; with c_l = 2*Gamma/(V*c) this is C_L = (1/S) integral c_l(y) c(y) dy)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
C_L = (1/S) * integral c_l(y) * c(y) dy
```

**⚠️ Divergence from the source.** The discrete area-weighted mean is the exact quadrature of the cited integral, since the weight c(y)dy IS the strip area. This is the best-founded quantity in the turbulator module.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:605-613`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
