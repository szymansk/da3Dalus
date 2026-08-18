---
name: v-stall
symbol: V_stall
kind: quantity
unit: m/s
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Stall speed

**Definition.** Speed at CL_max for the curve's mass.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
v_stall = float(np.sqrt(2.0 * weight_n / (rho * s_ref_m2 * cl_max))) if cl_max > 0 else None
```

**Inputs.**

- [[weight-n|Weight]]
- [[rho-speed-polar|Air density (speed polar)]]
- [[s-ref-speed-polar|Reference wing area]]
- [[cl-max-speed-polar|CL max for stall speed]]  — *⊣ limit*

**Produced by.** `app/services/analysis_service.py:524` — `_compute_speed_polar`

**Consumed by.**

- in this graph: `Speed-polar X-axis lower bound`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `SpeedPolarCurve.v_stall` · `frontend speed-polar chart`

**Source.** 🟢 SOURCED

> Sadraey §4.3.2 Eq. 4.30/4.31 (Wiley 2013)
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
L = W = ½·rho·V_s²·S·C_L,max  (4.30);  (W/S)_Vs = ½·rho·V_s²·C_L,max  (4.31)
```

**⚠️ Divergence from the source.** Exact match. Note Sadraey prescribes SEA-LEVEL rho as the conservative choice; the code uses rho at the requested sweep altitude, so V_stall is optimistic (lower) at altitude relative to the source's convention. Second producer alongside assumption_compute_service (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Second producer of V_stall: assumption_compute_service also emits v_stall_mps/v_s1_mps into the computation context that the chip row shows (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
