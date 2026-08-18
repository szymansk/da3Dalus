---
name: low-re-cl-max-safety-band
symbol: —
kind: parameter
unit: dimensionless (ΔCL)
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
---

# CL_max safety band

**Definition.** CL_max − cl_target margin at which the high-CL fallback Match reaches 1.0.

**Value.** `0.30`

**Formula — as the code writes it.**

```
low_re_score_cl_max_safety_band: float = 0.30
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/settings.py:107` — `Settings.low_re_score_cl_max_safety_band`

**Consumed by.**

- in this graph: [[alr-match|Match component of score_target_cl]]
- outside it: `score_target_cl:1035,1066`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source for a 0.30 ΔCL stall-margin band. The concept of a CL_max margin is standard; this magnitude is not attributable and is applied at section level, where the 2D-to-3D difference is unaccounted for.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `# CL_max margin (cl_max − cl_target) at which the high-CL Match component
# reaches 1.0.  Below 0 → score 0 (stall risk).  (gh-825 glide-point fix)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
