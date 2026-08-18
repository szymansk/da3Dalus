---
name: fe_cl_min
symbol: CL_min
kind: quantity
unit: -
cluster: perf-envelope
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Inverted maximum lift coefficient

**Definition.** Maximum negative lift coefficient assumed for inverted flight.

**Formula — as the code writes it.**

```
cl_min = -0.8 * cl_max
```

**Inputs.** [[fe_cl_max|Maximum lift coefficient (envelope)]] · [[fe_cl_min_factor|Negative CL_max ratio]]

**Produced by.** `app/services/flight_envelope_service.py:316` — `compute_vn_curve`

**Consumed by.**

- in this graph: [[fe_n_neg_maneuver|Negative maneuver load factor]]

**Source.** 🔴 NO SOURCE FOUND

> Inherits fe_cl_min_factor.
>
> — via `rc`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
