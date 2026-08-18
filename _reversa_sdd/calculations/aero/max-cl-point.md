---
name: max-cl-point
symbol: CLmax
kind: quantity
unit: mixed (deg, -, -)
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
---

# Maximum lift coefficient point

**Definition.** Sweep point with the largest CL — the CL_max estimate.

**Formula — as the code writes it.**

```
i = int(np.argmax(cl))
```

**Inputs.** [[cl-values|Lift coefficient array]] · [[alpha-array|Alpha sweep array]]

**Produced by.** `app/services/analysis_service.py:129` — `_compute_cl_cd_points`

**Consumed by.**

- in this graph: [[characteristic-points|Characteristic points dict]] · [[stall-fallback-index|Stall fallback index]] · [[stall-point|Stall point]]
- outside it: `alpha-sweep PNG` · `copilot_tools 'cl_max_point'` · `_find_stall_point`

**Source.** 🟢 SOURCED

> Anderson 6e §4.3 and §4.x 'Airfoil Stall' (c_l,max occurs just prior to stall); Sadraey §5.4.3 (feature 2: maximum lift coefficient C_l,max)
>
> — via `aerodynamics-expert, aircraft-design-scholz`

**The source states it as.**

```
c_l,max = peak of the c_l(α) curve, immediately preceding α_stall
```

**⚠️ Divergence from the source.** The source defines CL_max as a curve PEAK. The code takes np.argmax over the sweep, which returns the last α whenever the sweep terminates before the peak — reporting a monotonically rising endpoint as CL_max with no flag.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** CL_max is the discrete grid maximum — if the sweep ends before stall it silently returns the last alpha as CLmax.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
