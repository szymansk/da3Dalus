---
name: xnp-lat-values
symbol: X_np,lat
kind: quantity
unit: m
cluster: aero-spanwise
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Lateral neutral point array

**Definition.** Xnp_lat vs alpha pulled from result.reference.

**Formula — as the code writes it.**

```
np.atleast_1d(np.asarray(result.reference.Xnp_lat, dtype=float))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:868` — `_extract_reference_arrays`

**Consumed by.**

- in this graph: [[neutral-combined-metric|Neutral-point sensitivity metric]] · [[variation-span|Series span]] · [[xnp-lat-jump|Xnp_lat jump]] · [[xnp-lat-median-deviation|Xnp_lat outlier deviation]]
- outside it: `_collect_xnp_lat_labels` · `_compute_neutral_strip_colors` · `_classify_variation`

**Source.** 🔴 NO SOURCE FOUND

> No definition of a 'lateral neutral point' station found in Sadraey §11.6, Scholz, or Anderson 6e — directional stability is treated via C_nβ, not an x-station analogue. Xnp_lat is a solver-specific output.
>
> — via `aircraft-design-scholz, aerodynamics-expert`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
