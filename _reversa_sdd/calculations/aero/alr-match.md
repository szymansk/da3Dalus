---
name: alr-match
symbol: Match
kind: quantity
unit: dimensionless (0..1)
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/no-source-found
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Match component of score_target_cl

**Definition.** Drag-rise-based fit of the airfoil to the target CL, with a CL_max-margin fallback above r_poor.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
match_raw = 1.0 - (r - 1.0) / (r_poor - 1.0)
if tolerance_half > 0 and distance_from_sweet_spot < tolerance_half:
    frac = 1.0 - distance_from_sweet_spot / tolerance_half
    match = match_raw + (1.0 - match_raw) * frac * 0.5
    match = min(match, 1.0)
```

**Inputs.**

- [[alr-drag-rise-ratio|Relative drag-rise ratio r]]
- [[low-re-score-r-poor|Drag-rise ratio at which Match→0]]
- [[alr-tolerance-half|Match tolerance half-width]]
- [[alr-best-ld-cl|CL at maximum L/D (closed form)]]
- [[alr-cl-max|Section CL_max]]  — *⊣ limit*
- [[low-re-cl-max-safety-band|CL_max safety band]]  — *⤵ fallback*

**Produced by.** `app/services/airfoil_low_re_service.py:1071` — `score_target_cl`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `target-CL suitability score`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `score_target_cl:1085`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source for either branch. The two branches are structurally different formulas, so the score is discontinuous at r = r_poor — an artefact no source would sanction.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Two structurally different formulas produce 'Match' depending on whether r crosses r_poor, so the score is discontinuous at r = r_poor.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `match = min(margin / max(cl_max_safety_band, 1e-9), 1.0)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
