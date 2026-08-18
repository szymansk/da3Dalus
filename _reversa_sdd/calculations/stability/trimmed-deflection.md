---
name: trimmed-deflection
symbol: δ_trim
kind: quantity
unit: deg
cluster: stability
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - solver-adjacent/aerobuildup
---

# Trimmed control deflection

**Definition.** Control deflection at which the target aerodynamic coefficient is achieved.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
trimmed_deflection = brentq(residual, lower, upper, xtol=1e-6, maxiter=50)
...
trimmed_deflection=round(trimmed_deflection, 6),
```

**Inputs.**

- [[aerobuildup-trim-residual|AeroBuildup trim residual]]
- [[brentq-xtol|Brent root-finder tolerance]]  — *ε tolerance*
- [[brentq-maxiter|Brent root-finder iteration cap]]
- [[deflection-bounds|Trim search bounds]]  — *⊣ limit*

**Produced by.** `app/services/aerobuildup_trim_service.py:214` — `trim_with_aerobuildup`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Achieved target coefficient`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/aerobuildup_trim_service.py:236-242 (final re-run), :254, :309, :331` · `app/api/v2/endpoints/operating_points.py:214-216` · `app/services/retrim_service.py:22` · `frontend/hooks/useOperatingPoints.ts`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §12.5.4 Eq. 12.90 — the elevator deflection that satisfies longitudinal trim; §12.5.4 also defines the trim curve δ_E vs V as the primary design artefact. Numerical method: Brent 1973 Ch. 4 / scipy.optimize.brentq.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
δ_E = −[(T·z_T/(qSC̄) + C_mo)C_Lα + (C_L1 − C_Lo)C_mα] / [C_Lα·C_mδE − C_mα·C_LδE]   (Sadraey Eq. 12.90)
```

**⚠️ Divergence from the source.** Sadraey obtains δ_E in closed form from linearised derivatives; the code obtains it by root-finding on the full nonlinear solver. That is a legitimate (higher-fidelity) substitution, not an error. Rounded to 6 dp twice (lines 254/331 and again at 309 when passed to enrichment), so the enrichment's usage_fraction and the reported deflection can differ in the last digit.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Rounded to 6 dp twice (lines 254/331 and again at 309 when passed to enrichment) so the enrichment's usage_fraction and the reported deflection can differ in the last digit.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
