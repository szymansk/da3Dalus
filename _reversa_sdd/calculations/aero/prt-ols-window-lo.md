---
name: prt-ols-window-lo
symbol: CL_lo
kind: parameter
unit: dimensionless (CL)
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: unclassified-parameter
tags:
  - cluster/aero-polars
  - class/unclassified-parameter
  - source/no-source-found
  - flag/anomaly
  - flag/divergence
---

# OLS polar window lower CL bound

**Definition.** Lower CL bound of the linear polar window used for the parabolic OLS fit.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `0.10`

**Formula — as the code writes it.**

```
cl_lo = max(0.10, 0.10 * cl_max)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/polar_re_table_service.py:340` — `_fit_polar_ols`

**Consumed by.**

- in this graph: `Band cd0 (fitted intercept)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_fit_polar_ols:343`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 0.10 is unsourced. Also inert as written: max(0.10, 0.10·cl_max) equals 0.10 for every cl_max < 1.0, so the relative branch never fires at RC section levels.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** For any cl_max < 1.0 the max() makes the 0.10·cl_max term inert — the window floor is always the absolute 0.10.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `cl_lo = max(0.10, 0.10 * cl_max)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
