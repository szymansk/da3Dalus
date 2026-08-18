---
name: prt-k-fit
symbol: k
kind: quantity
unit: dimensionless
cluster: aero-polars
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/sourced
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Band induced-drag factor k

**Definition.** Slope of CD vs CL² for one V-band; converted to Oswald efficiency, never persisted.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
k, cd0_fit = np.polyfit(cl2_win, cd_win, deg=1)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/polar_re_table_service.py:372` — `_fit_polar_ols`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Band Oswald efficiency` · `Band OLS R²`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_fit_band_with_ar:281`

**Source.** 🟢 SOURCED

> Anderson 6e §6.7.2 — k = 1/(π e AR), the slope of C_D vs C_L²

**The source states it as.**

```
k = 1/(π e AR)
```

**⚠️ Divergence from the source.** Same form. Not persisted (deliberate, schema docstring line 8).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Deliberately excluded from PolarReTableRow (schema docstring line 8) — no consumer outside _fit_band_with_ar.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `if k <= 0:
    logger.debug("polar OLS: non-positive slope k=%.6f", k)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
