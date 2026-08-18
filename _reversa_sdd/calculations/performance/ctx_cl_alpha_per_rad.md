---
name: ctx_cl_alpha_per_rad
symbol: CL_alpha
kind: parameter
unit: 1/rad
cluster: perf-envelope
user_visible: false
source_status: SOURCED
---

# Cached lift-curve slope

**Definition.** Alpha-sweep regression slope read from assumption_computation_context.

**Formula — as the code writes it.**

```
val = ctx.get("cl_alpha_per_rad"); reject non-finite or <= 0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/flight_envelope_service.py:154` — `_extract_cl_alpha_from_context`

**Consumed by.**

- in this graph: [[fe_effective_cl_alpha|Effective lift-curve slope for gust]]

**Source.** 🟢 SOURCED

> Computed upstream from the AeroBuildup sweep — provenance belongs to the aero-context cluster, not here. Guard (finite, > 0) is correct.
>
> — via `aero`

**The source states it as.**

```
CL_alpha from alpha-sweep regression
```

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
