---
name: alr-drag-bucket-width
symbol: ΔCL_bucket
kind: quantity
unit: dimensionless (ΔCL)
cluster: aero-polars
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/divergence
---

# Drag bucket width

**Definition.** CL span over which CD stays within 15% of CD_min.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
bucket_mask = cd_f <= cd_threshold
result["drag_bucket_width"] = float(np.max(bucket_cl) - np.min(bucket_cl))
```

**Inputs.**

- [[alr-cd-min|Section CD_min]]  — *⊣ limit*
- [[alr-drag-bucket-factor|Drag-bucket CD threshold factor]]  — *⊣ limit*

**Produced by.** `app/services/airfoil_low_re_service.py:642` — `_extract_metrics`

**Consumed by.**

- in this graph: `re_agnostic suitability score` · `Match tolerance half-width`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `AirfoilLowRePolarModel.drag_bucket_width` · `score_re_agnostic:850` · `score_target_cl:1032,1049`

**Source.** 🟡 PARTIAL

> Abbott & von Doenhoff (1959), Ch. 6 / Appendix IV — low-drag range expressed as a ΔC_l span
>
> — via `aerodynamics-expert`

**The source states it as.**

```
low-drag range = Δc_l over which c_d stays low
```

**⚠️ Divergence from the source.** The quantity matches the source's concept; its numerical boundary (1.15·c_d,min) does not — see alr-drag-bucket-factor. A&vD's bucket is a 6-series laminar-flow phenomenon; at Re 40k–750k the bucket is governed by the laminar separation bubble instead, so the measured width is a different physical thing wearing the same name.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `result["drag_bucket_width"] = float(np.max(bucket_cl) - np.min(bucket_cl))`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
