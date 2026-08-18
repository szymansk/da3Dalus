---
name: alpha-array
symbol: α
kind: quantity
unit: deg
cluster: aero-spanwise
user_visible: true
source_status: PARTIAL
---

# Alpha sweep array

**Definition.** Angle-of-attack grid for the sweep, taken from the solver's flight_condition or rebuilt from the request.

**Formula — as the code writes it.**

```
np.linspace(start=sweep_request.alpha_start, stop=sweep_request.alpha_end, num=sweep_request.alpha_num)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:84` — `_extract_alpha_sweep_arrays`

**Consumed by.**

- in this graph: [[cm-gradient|Local Cm gradient]] · [[dcm-dalpha-slope|Longitudinal stability slope]] · [[drag-at-zero-lift-point|Drag at zero lift point]] · [[max-cl-point|Maximum lift coefficient point]] · [[max-ld-point|Maximum L/D point]] · [[min-cd-point|Minimum drag coefficient point]] · [[neutral-combined-metric|Neutral-point sensitivity metric]] · [[trim-point-cm-zero|Trim point (Cm = 0)]]
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
