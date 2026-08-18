---
name: prt-ols-window-hi
symbol: CL_hi
kind: parameter
unit: dimensionless (CL)
cluster: aero-polars
user_visible: false
source_status: PARTIAL
node_class: unclassified-parameter
tags:
  - cluster/aero-polars
  - class/unclassified-parameter
  - source/partial
  - flag/divergence
---

# OLS polar window upper CL bound

**Definition.** Upper CL bound of the OLS window, set at 85% of CL_max to avoid stall contamination.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `0.85`

**Formula — as the code writes it.**

```
cl_hi = 0.85 * cl_max
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/polar_re_table_service.py:341` — `_fit_polar_ols`

**Consumed by.**

- in this graph: `Band cd0 (fitted intercept)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_fit_polar_ols:343`

**Source.** 🟡 PARTIAL

> Anderson 6e §4.12.4 — the polar departs from parabolic as separation grows toward CL_max, so near-stall points must be excluded from a parabolic fit
>
> — via `aerodynamics-expert`

**⚠️ Divergence from the source.** The practice of truncating below stall is standard; the specific 0.85·CL_max fraction is not attributable to any source.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `cl_hi = 0.85 * cl_max`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
