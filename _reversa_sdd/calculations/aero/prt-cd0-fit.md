---
name: prt-cd0-fit
symbol: C_D0
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
  - flag/divergence
---

# Band cd0 (fitted intercept)

**Definition.** Zero-lift drag coefficient of one V-band from OLS of CD against CL².

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
k, cd0_fit = np.polyfit(cl2_win, cd_win, deg=1)
```

**Inputs.**

- [[prt-ols-window-lo|OLS polar window lower CL bound]]  — *⊣ limit*
- [[prt-ols-window-hi|OLS polar window upper CL bound]]  — *⊣ limit*

**Produced by.** `app/services/polar_re_table_service.py:372` — `_fit_polar_ols`

**Consumed by.**

- in this graph: `cd0 at query velocity` · `Band OLS R²`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_fit_band_with_ar:274,298` · `PolarReTableRow.cd0` · `lookup_cd0_at_v:131`

**Source.** 🟢 SOURCED

> Anderson 6e §6.7.2 — C_D = C_D0 + C_L²/(π e AR); OLS of CD on CL² is the standard identification of that polar
>
> — via `aerodynamics-expert`

**The source states it as.**

```
C_D = C_D0 + C_L²/(π e AR)
```

**⚠️ Divergence from the source.** Anderson's polar is symmetric about CL=0. The fit window is one-sided (0.10 ≤ CL ≤ 0.85·CL_max), so for a cambered wing whose CD_min sits at CL>0 the fitted intercept absorbs the offset and cd0 is biased low. Matters for the values users see.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `k, cd0_fit = np.polyfit(cl2_win, cd_win, deg=1)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
