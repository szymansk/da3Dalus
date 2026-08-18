---
name: variation-span
kind: quantity
unit: m (for Xnp)
cluster: aero-spanwise
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/no-source-found
  - surface/user-visible
---

# Series span

**Definition.** Max-minus-min range of a series (Xnp / Xnp_lat) used to call it robust/moderate/volatile.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
span = float(np.max(values) - np.min(values))
```

**Inputs.**

- [[xnp-values|Longitudinal neutral point array]]
- [[xnp-lat-values|Lateral neutral point array]]

**Produced by.** `app/services/analysis_service.py:845` — `_classify_variation`

**Consumed by.**

- outside it: `_render_summary_panel`

**Source.** 🔴 NO SOURCE FOUND

> Max-minus-min of a neutral-point series is an ad-hoc diagnostic; no source treats Xnp travel over an α-sweep as a design metric.
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
