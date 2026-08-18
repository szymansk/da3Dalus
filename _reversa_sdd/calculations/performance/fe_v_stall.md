---
name: fe_v_stall
symbol: V_s
kind: quantity
unit: m/s
cluster: perf-envelope
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Stall speed (1 g)

**Definition.** One-g stall speed at sea level from CL_max and wing loading.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
v_stall = math.sqrt(2 * weight / (rho * wing_area_m2 * cl_max))
```

**Inputs.**

- [[fe_weight|Aircraft weight]]
- [[fe_rho_default|Default air density (flight envelope)]]  — *⤵ fallback*
- [[fe_wing_area|Reference wing area]]  — *× unit*
- [[fe_cl_max|Maximum lift coefficient (envelope)]]  — *⤵ fallback*

**Produced by.** `app/services/flight_envelope_service.py:314` — `compute_vn_curve`

**Consumed by.**

- in this graph: `Velocity sweep points` · `KPI: best L/D speed` · `KPI: min sink speed` · `KPI: stall speed`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `VnDiagram.tsx`

**Source.** 🟢 SOURCED

> Direct inversion of L = 0.5*rho*V^2*S*CL with L = W; Anderson, Introduction to Flight, Ch. 6 (Elements of Airplane Performance), standard stall-speed relation.
>
> — via `aero`

**The source states it as.**

```
V_s = sqrt(2W/(rho*S*CL_max))
```

**⚠️ Divergence from the source.** Physics correct; provenance broken. Two producers of the same user-visible number — assumption_compute_service._stall_speed writes ctx['v_stall_mps']/ctx['v_s1_mps'] (SpeedChipRow, mission_kpi stall_safety) while fe:314 recomputes it for the V-n diagram and the stall_speed KPI. They can disagree whenever CL_max or mass resolve differently. ADR 0022.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Two producers of the same user-visible number: assumption_compute_service._stall_speed writes ctx['v_stall_mps'] / ctx['v_s1_mps'] (shown in SpeedChipRow and consumed by mission_kpi stall_safety), while this line recomputes it for the V-n diagram and the stall_speed KPI. ADR 0022.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
