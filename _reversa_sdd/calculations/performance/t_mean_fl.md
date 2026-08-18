---
name: t_mean_fl
symbol: T_mean
kind: quantity
unit: N
cluster: perf-matching
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Effective mean thrust

**Definition.** Static thrust after applying the (currently unity) de-rate factor.

**Formula — as the code writes it.**

```
t_mean = _T_STATIC_MEAN_FACTOR * t_static_N
```

**Inputs.** [[t_static_mean_factor|Static-thrust de-rate factor]]

**Produced by.** `app/services/field_length_service.py:201` — `_compute_s_to_ground`

**Consumed by.**

- in this graph: [[t_over_w_fl|Thrust-to-weight (field length)]]
- outside it: `t_over_w_fl:202`

**Source.** 🔴 NO SOURCE FOUND

> Inherits t_static_mean_factor: no source for the de-rate, and the value 1.0 makes this a no-op.
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Sadraey Eq. 4.66 integrates thrust across the ground roll rather than using a single mean value; the code's mean-thrust abstraction has no counterpart in the sources and currently carries no de-rate at all.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `# effective thrust [N]`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
