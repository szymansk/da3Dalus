---
name: alr-score-cd-min-ref
symbol: —
kind: constant
unit: dimensionless
cluster: aero-polars
user_visible: true
source_status: NO_SOURCE_FOUND
---

# CD_min reference for re_agnostic

**Definition.** CD_min that maps to a full 1.0 on the CD_min component.

**Value.** `0.008`

**Formula — as the code writes it.**

```
CD_MIN_REF = 0.008  # low CD_min
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:858` — `score_re_agnostic`

**Consumed by.**

- in this graph: [[alr-score-re-agnostic|re_agnostic suitability score]]
- outside it: `score_re_agnostic:880`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source for 0.008.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** c_d,min is strongly Re-dependent below Re ≈ 200k (Anderson 6e §20.3.2 shows the laminar/turbulent regime change dominating at Re_c = 100k); a single Re-independent target mis-ranks across the grid (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**Cited in the code itself.** `cd_score = min(CD_MIN_REF / cd_min, 1.0)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
