---
name: net-pitch-up
symbol: —
kind: quantity
unit: – (dimensionless)
cluster: stability
user_visible: false
source_status: PARTIAL
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/partial
  - flag/anomaly
  - flag/divergence
---

# Net nose-up moment coefficient

**Definition.** Sum of the aerodynamic-centre moment, full elevator authority and flap moment; the numerator of the trim inversion and the subject of the infeasibility guard.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
net_pitch_up = cm_ac + cm_delta_e * delta_e_max_rad + delta_cm_flap
```

**Inputs.**

- [[cm-ac|Aerodynamic-centre pitching moment]]
- [[cm-delta-e|Elevator authority (sign-enforced)]]
- [[delta-e-max-rad|Maximum elevator deflection (radians)]]
- [[delta-cm-flap|Flap-induced pitching moment]]  — *⊣ limit*

**Produced by.** `app/services/elevator_authority_service.py:236` — `_trim_inversion`

**Consumed by.**

- in this graph: `Forward CG limit (trim inversion)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/elevator_authority_service.py:237` · `app/services/elevator_authority_service.py:310,311,315,318 (_apply_infeasibility_guard, independent recomputation)`

**Source.** 🟡 PARTIAL

> Each term is sourced individually — C_m,ac from Sadraey §6.7.1 (C_mo,wf) and Anderson "Fundamentals of Aerodynamics" 6e §4.9 (moment about the aerodynamic centre); C_mδE·δ_E from Sadraey §12.5.2 Eq. 12.51 and the trim balance §12.5.4 Eq. 12.85 (C_mo + C_mα·α + C_mδE·δ_E = −T·z_T/(qSC̄)); ΔC_m,flap as the flap's pitching-moment contribution (Sadraey §5.12.2 notes the flap pitching-moment change explicitly). The specific three-term sum as a standalone 'net pitch-up' is not stated in any consulted source.
>
> — via `aircraft-design-scholz + aerodynamics-expert`

**The source states it as.**

```
Sadraey Eq. 12.85: C_mo + C_mα·α + C_mδE·δ_E = −T·z_T/(qSC̄)   — the moment balance includes the C_mα·α term and the thrust-offset term, both absent from the code's sum
```

**⚠️ Divergence from the source.** The literature moment balance carries two terms the code drops: the angle-of-attack contribution C_mα·α and the thrust-line offset moment T·z_T/(qSC̄). Sadraey §6.7.1 lists the full balance M_owf + M_Lwf + M_Lh + M_oh + M_Teng + M_Dw = 0 and explicitly notes which terms are dropped 'in educational practice'. Computed twice independently in the code (lines 236 and 310).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Computed twice, independently, from the same inputs (lines 236 and 310) — two producers of one number.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Anderson §7.7 — forward CG limit from elevator authority at landing stall`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
