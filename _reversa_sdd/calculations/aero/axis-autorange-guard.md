---
name: axis-autorange-guard
kind: constant
unit: -
cluster: aero-spanwise
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/aero-spanwise
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
---

# Axis-bound sanity guard

**Definition.** Both axis bounds are dropped to autorange when one is missing or they are inverted.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Formula — as the code writes it.**

```
if v_axis_min is None or v_axis_max is None: v_axis_min = None; v_axis_max = None; elif v_axis_min >= v_axis_max: v_axis_min = None; v_axis_max = None
```

**Inputs.**

- [[v-axis-min|Speed-polar X-axis lower bound]]  — *⊣ limit*
- [[v-axis-max|Speed-polar X-axis upper bound]]  — *⊣ limit*

**Produced by.** `app/services/analysis_service.py:568` — `_compute_speed_polar`

**Consumed by.**

- outside it: `SpeedPolar`

**Source.** 🔴 NO SOURCE FOUND

> Plot-range sanity logic; no domain source.
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
