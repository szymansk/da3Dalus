---
name: tos-l-d-clean
symbol: l_d_clean
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Clean lift-to-drag ratio

**Definition.** CL divided by the area-weighted clean section profile drag.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
l_d_clean = cl / cd_clean if cd_clean > 0 else float("nan")
```

**Inputs.**

- [[tos-cl-avg|Area-weighted mean section CL]]
- [[tos-cd-clean-avg|Area-weighted mean clean section drag]]

**Produced by.** `app/services/turbulator_optimizer_service.py:343` — `compute_ld_summary`

**Consumed by.**

- in this graph: `L/D improvement`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/schemas/turbulator_optimizer.py:TurbulatorOptimizerSummarySchema.l_d_clean` · `frontend/components/workbench/TurbulatorEditDialog.tsx:339`

**Source.** 🟡 PARTIAL

> Anderson, Fundamentals of Aerodynamics 6e, §5.1 (C_D = c_d + C_D,i — total drag of a finite wing includes induced drag); Scholz, Flugzeugentwurf 05_PreliminarySizing §5.6.2 (E = C_L/C_D, E_max = 0.5*sqrt(pi*A*e/C_D0))
>
> — via `aerodynamics-expert, aircraft-design-scholz`

**The source states it as.**

```
L/D = C_L / C_D with C_D the TOTAL drag coefficient
```

**⚠️ Divergence from the source.** Real and user-visible. The denominator here is the area-weighted 2-D SECTION PROFILE drag only: no induced drag, no fuselage/tail/gear parasite drag, no interference. Per the cited Anderson relation the true C_D is strictly larger, so the displayed absolute L/D is unconditionally optimistic — for a typical RC wing (cd ~ 0.015, CL ~ 0.6) this reports ~40 while a real aircraft L/D at that scale is far lower. Only delta_l_d is defensible.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** The gap is worst at this scale: at AR ~ 6-8 and RC Reynolds numbers, induced drag is a large fraction of total drag at the cruise CL, so omitting it is not a small correction.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Named and displayed as L/D but the denominator is the section PROFILE drag only — no induced drag and no non-wing parasite drag — so the shown value is far above the aircraft's real L/D.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:343`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
