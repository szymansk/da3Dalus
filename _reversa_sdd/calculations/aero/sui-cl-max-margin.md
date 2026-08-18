---
name: sui-cl-max-margin
symbol: —
kind: quantity
unit: dimensionless (ΔCL)
cluster: aero-polars
user_visible: true
source_status: PARTIAL
---

# cl_max_margin

**Definition.** Section CL_max minus the largest resolved target CL; negative means stall risk.

**Formula — as the code writes it.**

```
cl_max_margin = cl_max_val - max(target_cls)
```

**Inputs.** [[alr-cl-max|Section CL_max]] · [[sui-target-cl-cruise|target_cl_cruise]] · [[sui-target-cl-best-glide|target_cl_best_glide]] · [[sui-target-cl-min-sink|target_cl_min_sink]]

**Produced by.** `app/services/suitability_service.py:531` — `search_suitability`

**Consumed by.**

- outside it: `SuitabilityItem.cl_max_margin:566` · `frontend AirfoilSuitabilityCard.tsx:398`

**Source.** 🟡 PARTIAL

> Anderson 6e §4.12.4 — C_l,max at the stalling angle bounds the usable lift range
>
> — via `aerodynamics-expert`

**⚠️ Divergence from the source.** Margin-to-stall is a standard idea; no source prescribes this exact difference. Real defect: cl_max comes from the slider-Re polar while the target CLs come from per-lens Re polars (gh-838), so the margin subtracts quantities evaluated at two different Reynolds numbers.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Compared at section level with no 2D→3D correction, while the caveat text itself concedes 'Section CL ≈ wing CL' only holds for an ideal elliptic untwisted wing.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** cl_max is taken from the slider-Re polar while the target CLs come from per-lens Re polars (gh-838) — margin mixes two Reynolds numbers.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `cl_max_margin = cl_max_val - max(target_cls)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
