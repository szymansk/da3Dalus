---
name: cl-max-speed-polar
symbol: C_L,max
kind: quantity
unit: -
cluster: aero-spanwise
user_visible: false
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/sourced
  - flag/anomaly
---

# CL max for stall speed

**Definition.** Maximum CL over the whole polar array, used for V_stall.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cl_max = float(np.max(cl_arr)) if cl_arr.size else 0.0
```

**Inputs.**

- [[cl-values|Lift coefficient array]]

**Produced by.** `app/services/analysis_service.py:482` — `_compute_speed_polar`

**Consumed by.**

- in this graph: `Alpha at stall` · `Stall speed`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> Anderson 6e §4.3 / §4.x Airfoil Stall ('V_stall ∝ 1/sqrt(c_l,max)'); Sadraey §5.4.3
>
> — via `aerodynamics-expert, aircraft-design-scholz`

**The source states it as.**

```
c_l,max = peak of c_l(α); sets stall speed via ½·rho·V_s²·S·C_L,max = m·g
```

**⚠️ Anomaly.** Second CL_max producer alongside max-cl-point (line 129) — same array, two independent argmax/max calls.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
