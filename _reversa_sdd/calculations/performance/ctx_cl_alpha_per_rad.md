---
name: ctx_cl_alpha_per_rad
symbol: CL_alpha
kind: parameter
unit: 1/rad
cluster: perf-envelope
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: unclassified-parameter
tags:
  - cluster/perf-envelope
  - class/unclassified-parameter
  - source/sourced
  - audit/confirmed
---

# Cached lift-curve slope

**Definition.** Alpha-sweep regression slope read from assumption_computation_context.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Formula — as the code writes it.**

```
val = ctx.get("cl_alpha_per_rad"); reject non-finite or <= 0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/flight_envelope_service.py:154` — `_extract_cl_alpha_from_context`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Effective lift-curve slope for gust`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

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
