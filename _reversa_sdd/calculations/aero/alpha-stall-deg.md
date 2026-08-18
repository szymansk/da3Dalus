---
name: alpha-stall-deg
symbol: α_stall
kind: quantity
unit: deg
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Alpha at stall

**Definition.** Angle of attack corresponding to CL_max via the linear lift-curve regression.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
alpha_stall_deg_val = _cl_to_alpha_deg(cl_max, cl_alpha_per_rad, alpha_0_deg)
```

**Inputs.**

- [[cl-max-speed-polar|CL max for stall speed]]  — *⊣ limit*
- [[cl-alpha-per-rad|Lift-curve slope from context]]
- [[alpha-0-deg|Zero-lift angle from context]]

**Produced by.** `app/services/analysis_service.py:488` — `_compute_speed_polar`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `SpeedPolarCurve.alpha_stall_deg (API only)`

**Source.** 🟢 SOURCED

> Anderson 6e §4.3 (linear lift-curve region, lift slope a₀, zero-lift angle α_L=0); Sadraey §5.4.3
>
> — via `aerodynamics-expert, aircraft-design-scholz`

**The source states it as.**

```
C_L = C_Lα·(α − α_0) in the LINEAR region only; α_stall is where C_L peaks, i.e. where the curve has already left the linear region
```

**⚠️ Divergence from the source.** MATERIAL. The code inverts the LINEAR lift-curve regression at C_L = C_L,max. Both sources state C_L,max lies at or past the bend-over of the lift curve, so the linear inverse systematically OVER-estimates α_stall (the real curve reaches C_L,max at a lower α than the linear extrapolation predicts). Magnitude grows with how soft the stall is (Anderson: trailing-edge stall on >16% thick sections bends over gradually).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** No consumer downstream of the API: frontend/hooks/useAnalysis.ts SpeedPolarCurve (lines 29-41) omits the three alpha_* fields; the UI reads ctx.alpha_stall_deg from the computation context instead (SpeedChipRow.tsx:40).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
