---
name: alr-tolerance-half
symbol: —
kind: quantity
unit: dimensionless (ΔCL)
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/no-source-found
  - flag/anomaly
  - flag/divergence
---

# Match tolerance half-width

**Definition.** Half-width of the forgiving zone around cl_star, scaled by the airfoil's drag bucket.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
tolerance_half = (bucket_width / max(bucket_ref, 1e-9)) * 0.5
```

**Inputs.**

- [[alr-drag-bucket-width|Drag bucket width]]
- [[low-re-bucket-tolerance-ref|Bucket tolerance reference width]]

**Produced by.** `app/services/airfoil_low_re_service.py:1049` — `score_target_cl`

**Consumed by.**

- in this graph: `Match component of score_target_cl`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `score_target_cl:1072,1073`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** The trailing 0.5 is an unnamed magic factor, and the expression is dimensionally inconsistent with its use: bucket_width/bucket_ref is dimensionless, yet the result is compared against distance_from_sweet_spot, which is in CL units. Only accidentally scaled because bucket_ref is O(1).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The trailing 0.5 is an unnamed magic factor; the ratio is dimensionless while distance_from_sweet_spot it is compared against is in CL units.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `tolerance_half = (bucket_width / max(bucket_ref, 1e-9)) * 0.5`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
