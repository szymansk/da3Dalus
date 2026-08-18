---
name: xnp-values
symbol: X_np
kind: quantity
unit: m
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
---

# Longitudinal neutral point array

**Definition.** Xnp vs alpha pulled from result.reference.

**Formula — as the code writes it.**

```
np.atleast_1d(np.asarray(result.reference.Xnp, dtype=float))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:862` — `_extract_reference_arrays`

**Consumed by.**

- in this graph: [[neutral-combined-metric|Neutral-point sensitivity metric]] · [[variation-span|Series span]] · [[xnp-median-deviation|Xnp outlier deviation]]
- outside it: `_plot_neutral_points` · `_classify_variation` · `_render_summary_panel`

**Source.** 🟢 SOURCED

> Sadraey, Aircraft Design: A Systems Engineering Approach (Wiley 2013), §11.6.2 Eq. 11.17/11.18; Anderson 6e §4.x (aerodynamic centre, dc_m/dα = 0)
>
> — via `aircraft-design-scholz, aerodynamics-expert`

**The source states it as.**

```
C_mα = C_Lα * (X_cg − X_np)  (11.17);  SM = (x_np − x_cg)/C̄  (11.18)
```

**⚠️ Divergence from the source.** Sadraey's X_np is NON-DIMENSIONAL (fraction of MAC); the code carries Xnp in metres. Any threshold applied to it therefore is not comparable to literature static-margin bands.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Only reaches the user through the alpha-sweep PNG; the JSON alpha_sweep response does not carry Xnp.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
