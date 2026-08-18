---
name: alr-alpha-sweep
symbol: α
kind: parameter
unit: deg
cluster: aero-polars
user_visible: false
source_status: PARTIAL
---

# Alpha sweep bounds and step

**Definition.** Angle-of-attack sweep evaluated at every Re grid point.

**Value.** `alpha_start=-5.0, alpha_end=18.0, alpha_step=0.2`

**Formula — as the code writes it.**

```
alpha_deg = np.arange(alpha_start, alpha_end + alpha_step * 0.5, alpha_step)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:464` — `compute_airfoil_low_re`

**Consumed by.**

- in this graph: [[alr-alpha-attached-window|Attached-flow alpha window]] · [[alr-cd-min|Section CD_min]] · [[alr-cl-max|Section CL_max]] · [[alr-cl-valid-range|Polar-fit validity CL range]] · [[alr-ld-max|Section (L/D)_max]] · [[alr-polar-cd0|Airfoil cd0 (parabolic fit vertex)]] · [[alr-polar-cl0|CL at minimum drag (cl0)]] · [[alr-polar-k|Airfoil polar curvature k]] · [[alr-stall-gentleness|Stall gentleness]]
- outside it: `get_aero_from_neuralfoil:470` · `_windowed_min_confidence:559`

**Source.** 🟡 PARTIAL

> Sharpe (2024), §7.2.5 — NeuralFoil training α distribution: 95% within [−17°, +18°], full range [−27.9°, +28.6°]
>
> — via `aerosandbox-expert`

**⚠️ Divergence from the source.** The 18° upper bound is exactly the edge of NeuralFoil's well-sampled α band, so extending it would enter thinner training data. But nothing in the code says that, and the practical consequence stands: a high-camber low-Re section that peaks above 18° has CL_max silently truncated at the sweep edge, which then propagates into cl_max_margin and every CL_max-referenced score. The 0.2° step has no source.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Hard upper bound of 18° can truncate CL_max for high-camber / high-lift sections, silently capping cl_max at the sweep edge.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `alpha_deg = np.arange(alpha_start, alpha_end + alpha_step * 0.5, alpha_step)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
