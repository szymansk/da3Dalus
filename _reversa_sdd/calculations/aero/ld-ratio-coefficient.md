---
name: ld-ratio-coefficient
symbol: L/D
kind: quantity
unit: -
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
---

# Lift-to-drag ratio (coefficient form)

**Definition.** Point-wise CL/CD used to locate the best-glide point.

**Formula — as the code writes it.**

```
ld = np.where(np.abs(cd) > 1e-12, cl / cd, np.nan)
```

**Inputs.** [[cl-values|Lift coefficient array]] · [[cd-values|Drag coefficient array]] · [[divide-guard-epsilon|Division guard epsilon]]

**Produced by.** `app/services/analysis_service.py:108` — `_compute_cl_cd_points`

**Consumed by.**

- in this graph: [[max-ld-point|Maximum L/D point]]

**Source.** 🟢 SOURCED

> Anderson 6e §6.7.2 (Maximum Lift-to-Drag Ratio)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
L/D = C_L / C_D
```

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
