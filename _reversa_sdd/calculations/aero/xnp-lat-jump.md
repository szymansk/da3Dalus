---
name: xnp-lat-jump
kind: quantity
unit: m
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

# Xnp_lat jump

**Definition.** Largest step-to-step change in Xnp_lat, labelled as a jump.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
jumps = np.abs(np.diff(lat_curve)); jump_idx = int(np.nanargmax(jumps)) + 1
```

**Inputs.**

- [[xnp-lat-values|Lateral neutral point array]]

**Produced by.** `app/services/analysis_service.py:1234` — `_collect_xnp_lat_labels`

**Consumed by.**

- outside it: `alpha-sweep PNG panel 5`

**Source.** 🔴 NO SOURCE FOUND

> Largest first-difference labelled as a 'jump'; unconditional, no source.
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
