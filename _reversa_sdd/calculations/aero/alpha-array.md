---
name: alpha-array
symbol: α
kind: quantity
unit: deg
cluster: aero-spanwise
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Alpha sweep array

**Definition.** Angle-of-attack grid for the sweep, taken from the solver's flight_condition or rebuilt from the request.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
np.linspace(start=sweep_request.alpha_start, stop=sweep_request.alpha_end, num=sweep_request.alpha_num)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:84` — `_extract_alpha_sweep_arrays`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Local Cm gradient` · `Longitudinal stability slope` · `Drag at zero lift point` · `Maximum lift coefficient point` · `Maximum L/D point` · `Minimum drag coefficient point` · `Neutral-point sensitivity metric` · `Trim point (Cm = 0)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_compute_alpha_sweep_characteristic_points` · `get_alpha_sweep_diagram_url` · `copilot_tools._run_polar_async:366` · `frontend/hooks/useAnalysis.ts extractResult`

**Source.** 🟡 PARTIAL

> Anderson, Fundamentals of Aerodynamics 6e, §4.3 (lift curve: c_l vs α, linear region then stall)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
α = angle between freestream and chord line; c_l = f(α)
```

**⚠️ Divergence from the source.** Source defines α as the physical independent variable; the uniform np.linspace grid and its resolution are a numerics choice with no literature basis. Every downstream 'characteristic point' is grid-quantised.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
