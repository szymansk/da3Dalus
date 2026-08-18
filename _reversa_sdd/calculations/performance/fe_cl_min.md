---
name: fe_cl_min
symbol: CL_min
kind: quantity
unit: -
cluster: perf-envelope
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/no-source-found
---

# Inverted maximum lift coefficient

**Definition.** Maximum negative lift coefficient assumed for inverted flight.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cl_min = -0.8 * cl_max
```

**Inputs.**

- [[fe_cl_max|Maximum lift coefficient (envelope)]]  — *⤵ fallback*
- [[fe_cl_min_factor|Negative CL_max ratio]]  — *⊣ limit*

**Produced by.** `app/services/flight_envelope_service.py:316` — `compute_vn_curve`

**Consumed by.**

- in this graph: `Negative maneuver load factor`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🔴 NO SOURCE FOUND

> Inherits fe_cl_min_factor.
>
> — via `rc`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
