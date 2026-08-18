---
name: alpha_trimmed
symbol: α
kind: quantity
unit: rad (stored) / deg (solved)
cluster: perf-oppoints
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/perf-oppoints
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/divergence
---

# Trimmed angle of attack

**Definition.** Final solved angle of attack, stored in radians.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
alpha_rad=math.radians(best_alpha)
```

**Inputs.**

- [[trim_objective|Opti trim objective]]
- [[grid_alpha_sweep|Grid-search alpha sweep]]  — *⤵ fallback*
- [[alpha_bounds_opti|Opti alpha bounds and initial guess]]  — *⊣ limit*

**Produced by.** `app/services/operating_point_generator_service.py:990` — `_trim_or_estimate_point`

**Consumed by.**

- in this graph: `Aero coefficients at the trimmed point` · `ALPHA_LIMIT_REACHED warning`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/models/analysismodels.py (alpha column)` · `app/services/operating_point_generator_service.py:1164 (compute_enrichment alpha_deg)` · `app/services/section_aoa_service.py` · `app/services/retrim_service.py` · `frontend/components/workbench/OperatingPointsPanel.tsx`

**Source.** 🟢 SOURCED

> AeroSandbox 4.2 OperatingPoint: 'alpha = degrees, angle of attack'; 'rates are radians, angles are degrees — easy to mix up'
>
> — via `aerosandbox-expert`

**⚠️ Divergence from the source.** The solve is in degrees (matching ASB) and storage is in radians (app convention). Both are internally consistent; the conversion is explicit. The ASB documentation flags this exact deg/rad mix-up as a common error, so the dual representation is a maintenance hazard worth a comment, not a defect.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
