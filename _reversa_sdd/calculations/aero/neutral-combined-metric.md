---
name: neutral-combined-metric
kind: quantity
unit: m/deg
cluster: aero-spanwise
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Neutral-point sensitivity metric

**Definition.** Sum of the absolute alpha-gradients of Xnp and Xnp_lat.

**Formula — as the code writes it.**

```
gx = np.abs(np.gradient(xnp_curve, x_axis)); gy = np.abs(np.gradient(xnp_lat_curve, x_axis)); combined_metric = gx + gy
```

**Inputs.** [[xnp-values|Longitudinal neutral point array]] · [[xnp-lat-values|Lateral neutral point array]] · [[alpha-array|Alpha sweep array]]

**Produced by.** `app/services/analysis_service.py:1254` — `_compute_neutral_strip_colors`

**Consumed by.**

- in this graph: [[neutral-strip-percentiles|Neutral-trend percentile thresholds]]

**Source.** 🔴 NO SOURCE FOUND

> Summing \|dXnp/dα\| + \|dXnp_lat/dα\| mixes a longitudinal and an undefined lateral quantity; no source supports the combination.
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
