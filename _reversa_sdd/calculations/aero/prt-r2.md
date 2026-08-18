---
name: prt-r2
symbol: R²
kind: quantity
unit: dimensionless
cluster: aero-polars
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Band OLS R²

**Definition.** Coefficient of determination of the per-band parabolic polar fit.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
```

**Inputs.**

- [[prt-cd0-fit|Band cd0 (fitted intercept)]]
- [[prt-k-fit|Band induced-drag factor k]]

**Produced by.** `app/services/polar_re_table_service.py:385` — `_fit_polar_ols`

**Consumed by.**

- outside it: `_fit_band_with_ar:300` · `PolarReTableRow.r2 (app/schemas/polar_re_table.py:37)`

**Source.** 🟢 SOURCED

> Standard OLS coefficient of determination R² = 1 − SS_res/SS_tot (any regression text, e.g. Draper & Smith, Applied Regression Analysis 3e, Ch. 1)

**The source states it as.**

```
R² = 1 − SS_res/SS_tot
```

**⚠️ Divergence from the source.** Correct form. Persisted on PolarReTableRow but no reader anywhere in app/, scripts/ or frontend/ — a quality number nothing consumes.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Stored in the row schema but no reader was found in app/, scripts/ or frontend/ — a reported quality number nothing consumes.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `ss_res = float(np.sum((cd_win - (k * cl2_win + cd0_fit)) ** 2))
ss_tot = float(np.sum((cd_win - np.mean(cd_win)) ** 2))
r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
