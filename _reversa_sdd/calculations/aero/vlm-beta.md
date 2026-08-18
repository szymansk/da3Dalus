---
name: vlm-beta
symbol: beta
kind: quantity
unit: deg
cluster: aero-strips
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
  - solver-adjacent/vlm
---

# Echoed sideslip angle

**Definition.** Operating-point beta echoed into the strip-forces result.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
"beta": float(op_point.beta),
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/vlm_strip_forces.py:316` — `compute_vlm_strip_forces`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/analysis_service.py:_build_strip_forces_response` · `app/services/spanwise_loads.py:115`

**Source.** 🟢 SOURCED

> AeroSandbox docs_aero_3d.md, VortexLatticeMethod ('Beta sign convention' — a 4.0.7 bugfix corrected a sign error in compute_rotation_matrix_wind_to_geometry that flipped beta inside VLM analyses from 4.0.0)
>
> — via `aerosandbox-expert`

**⚠️ Divergence from the source.** Definition standard. Version-sensitive: any lateral result from this path is only trustworthy on ASB >= 4.0.7, and the beta bug compounds with the vlm-lift-direction defect, which is itself a beta-only error.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:316`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
