---
name: sui-caveat-text
symbol: —
kind: quantity
unit: text
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

# Suitability caveat block

**Definition.** Fixed disclaimer text plus an XFoil recommendation when any item is low-confidence.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
caveat_text = ("Relative ranking only. " "No hysteresis or laminar-bubble modelling. " "Section CL ≈ wing CL (ideal elliptic, untwisted). " "Tip-Re CL_max collapse not modelled — check tip_re_flag and cl_max_margin.")
```

**Inputs.**

- [[alr-min-analysis-confidence|Windowed min analysis confidence]]  — *⤵ fallback*
- [[low-re-low-confidence-flag|Low-confidence flag threshold]]  — *⊣ limit*

**Produced by.** `app/services/suitability_service.py:673` — `search_suitability`

**Consumed by.**

- outside it: `SuitabilityCaveat:701 → API response` · `frontend AirfoilSuitabilityCard.tsx`

**Source.** 🟢 SOURCED

> Claim by claim: 'no hysteresis' — Sharpe (2024) §7.1, NeuralFoil is single-valued by construction, unlike XFoil which exhibits α-sweep hysteresis; 'no laminar-bubble modelling' — Sharpe §7.2.4, the LSB regime is where the surrogate's own confidence collapses; 'Section CL ≈ wing CL (ideal elliptic, untwisted)' — Anderson 6e §5.3.1, the elliptical lift distribution is the case in which local c_l equals wing C_L; 'Tip-Re CL_max collapse' — RC-Network Wiki 'Re-Zahl', coefficients change strongly with Re near Re_crit
>
> — via `aerodynamics-expert, aerosandbox-expert, rc-aircraft-designer`

**⚠️ Divergence from the source.** Each of the four technical claims is attributable and each is stated correctly. This is the only user-facing text in the cluster whose content is fully defensible — the caveat is more rigorous than most of the numbers it caveats.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `"Relative ranking only. "
"No hysteresis or laminar-bubble modelling. "
"Section CL ≈ wing CL (ideal elliptic, untwisted). "`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
