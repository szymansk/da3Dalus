---
name: alr-cd-min
symbol: CD_min
kind: quantity
unit: dimensionless
cluster: aero-polars
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Section CD_min

**Definition.** Minimum drag coefficient over the trusted sweep at one Re.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
idx_cd_min = int(np.argmin(cd_f))
cd_min = float(cd_f[idx_cd_min])
```

**Inputs.**

- [[alr-alpha-sweep|Alpha sweep bounds and step]]  — *⊣ limit*
- [[alr-confidence-gate|NeuralFoil confidence gate]]

**Produced by.** `app/services/airfoil_low_re_service.py:628` — `_extract_metrics`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Drag-bucket CD threshold factor` · `Drag bucket width` · `re_agnostic suitability score`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `AirfoilLowRePolarModel.cd_min` · `score_re_agnostic:852`

**Source.** 🟢 SOURCED

> Abbott & von Doenhoff (1959), Ch. 6 and Appendix IV — c_d,min is a standard tabulated section characteristic

**The source states it as.**

```
c_d,min = min over the polar
```

**⚠️ Divergence from the source.** Same. Restricted here to the confidence-gated α range.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `idx_cd_min = int(np.argmin(cd_f))
cd_min = float(cd_f[idx_cd_min])`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
