---
name: neutral-combined-metric
kind: quantity
unit: m/deg
cluster: aero-spanwise
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
---

# Neutral-point sensitivity metric

**Definition.** Sum of the absolute alpha-gradients of Xnp and Xnp_lat.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
gx = np.abs(np.gradient(xnp_curve, x_axis)); gy = np.abs(np.gradient(xnp_lat_curve, x_axis)); combined_metric = gx + gy
```

**Inputs.**

- [[xnp-values|Longitudinal neutral point array]]
- [[xnp-lat-values|Lateral neutral point array]]
- [[alpha-array|Alpha sweep array]]

**Produced by.** `app/services/analysis_service.py:1254` — `_compute_neutral_strip_colors`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Neutral-trend percentile thresholds`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🔴 NO SOURCE FOUND

> Summing \|dXnp/dα\| + \|dXnp_lat/dα\| mixes a longitudinal and an undefined lateral quantity; no source supports the combination.
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
