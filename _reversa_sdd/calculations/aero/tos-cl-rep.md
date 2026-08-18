---
name: tos-cl-rep
symbol: cl_rep
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/partial
  - audit/confirmed
  - flag/divergence
---

# Representative lift coefficient (whole scope)

**Definition.** Area-weighted mean section CL used for the whole-wing trip optimisation.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cl_rep = sum(s.cl * s.section_area_m2 for s in sections) / total_area if total_area > 0 else sections[len(sections) // 2].cl
```

**Inputs.**

- [[saoa-cl|Section lift coefficient (Kutta-Joukowski)]]
- [[bwsd-section-area-normalised|Normalised section area]]

**Produced by.** `app/services/turbulator_optimizer_service.py:546` — `run_turbulator_optimizer`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Whole-wing optimal trip position`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟡 PARTIAL

> Anderson, Fundamentals of Aerodynamics 6e, §5.3 (C_L = (1/S) * integral c_l(y) c(y) dy — the area-weighted spanwise mean of c_l IS the wing C_L)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
C_L = (1/S) integral c_l(y) c(y) dy
```

**⚠️ Divergence from the source.** The weighting is exactly right as a definition of the wing-mean cl. Whether a single (cl, Re) pair can stand in for the whole wing in a trip optimisation is the unsourced part — see tos-global-xtr-opt.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:546-550`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
