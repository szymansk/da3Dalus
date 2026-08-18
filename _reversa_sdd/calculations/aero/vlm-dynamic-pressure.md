---
name: vlm-dynamic-pressure
symbol: q
kind: quantity
unit: Pa
cluster: aero-strips
user_visible: false
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
  - flag/anomaly
  - flag/divergence
---

# Freestream dynamic pressure

**Definition.** Dynamic pressure used to non-dimensionalise per-strip lift and drag.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
q = float(op_point.dynamic_pressure())
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/vlm_strip_forces.py:214` — `compute_vlm_strip_forces`

**Consumed by.**

- in this graph: `Local strip drag coefficient` · `Local strip lift coefficient`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §1.5 (definition of dynamic pressure)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
q_inf = 0.5 * rho_inf * V_inf^2
```

**⚠️ Divergence from the source.** None in form. The defect is duplication: analysis_service.py:2054 recomputes the identical quantity for the same run.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Second producer of dynamic pressure: analysis_service.py:2054 computes q_dyn = 0.5 * rho * velocity**2 independently for the same run (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:214`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
